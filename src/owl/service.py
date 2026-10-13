import logging
from typing import Any

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from src.core.settings import settings

logger = logging.getLogger(__name__)


class OwlService:
    def __init__(self):
        self.default_model = "gemini-1.5-flash"
        self.default_temp = 0.5
        self.embed_model = "models/gemini-embedding-001"

    def _l2_normalize(self, vec: list[float]) -> list[float]:
        v = np.array(vec)
        denom = np.linalg.norm(v)
        if denom == 0.0 or not np.isfinite(denom):
            return vec
        return (v / denom).tolist()

    async def _get_gemini_embedding(
        self, text: str, api_key: str | None = None, output_dimensionality: int | None = None
    ) -> list[float]:
        """Uses the Gemini API to get text embeddings, removing the need for local heavy models."""
        from google import genai

        try:
            key = api_key or settings.GOOGLE_API_KEY
            if not key:
                raise ValueError("Google API key not configured for embeddings.")

            client = genai.Client(api_key=key)
            if output_dimensionality:
                config = genai.types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY",
                    output_dimensionality=output_dimensionality,
                )
            else:
                config = genai.types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
            result = client.models.embed_content(model=self.embed_model, contents=text, config=config)
            embeddings = result.embeddings
            if not embeddings or not embeddings[0].values:
                raise ValueError("Gemini returned no embedding.")
            return list(embeddings[0].values)
        except Exception as e:
            logger.error(f"Gemini embedding failed: {e}")
            raise e

    def _coerce_doc_for_context(self, row: dict) -> dict:
        title = row.get("title") or row.get("report_title") or row.get("headline") or "Untitled"
        source = (
            row.get("source") or row.get("organization_name") or row.get("publisher") or row.get("origin") or "Unknown"
        )
        page = row.get("page_label") or row.get("page") or row.get("page_no") or ""
        url = row.get("URL") or row.get("url") or row.get("link") or row.get("report_url") or ""
        body = row.get("combined_details") or row.get("document") or row.get("summary") or row.get("content") or ""
        return {"title": title, "source": source, "page_label": page, "URL": url, "combined_details": body}

    def _build_prompt(self, user_question: str, docs: list, max_docs: int = 10) -> str:
        system_prompt = (
            "You are a Q&A assistant dedicated to providing accurate, up-to-date information "
            "from ReliefWeb (OCHA). Use ONLY the provided context documents to answer. "
            "If the answer is not in the context or you are unsure, say you do not know. "
            "Be clear and concise. Keep to ten sentences max. "
            "End by inviting the user to ask more."
        )
        chunks = []
        for i, d in enumerate(docs[:max_docs], start=1):
            meta = f"[{i}] {d['title']} — {d['source']}"
            if d.get("page_label"):
                meta += f" (p. {d['page_label']})"
            if d.get("URL"):
                meta += f" — {d['URL']}"
            chunks.append(f"{meta}\n{d.get('combined_details', '')}")
        context_block = "\n\n---\n\n".join(chunks) if chunks else "No context documents."
        return (
            f"{system_prompt}\n\n"
            f"### Context documents\n{context_block}\n\n"
            f"### User question\n{user_question}\n\n"
            f"### Your answer"
        )

    def _call_gemini_safe(self, prompt: str, model: str, temperature: float, api_key: str | None = None) -> str:
        from google import genai

        try:
            key = api_key or settings.GOOGLE_API_KEY
            if not key:
                return "⚠️ Gemini API key not configured."

            client = genai.Client(api_key=key)
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"temperature": temperature},
            )
            return resp.text if resp and resp.text else "⚠️ No response text from Gemini."
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            return f"⚠️ Gemini call failed: {e}"

    def _response_from_rows(
        self,
        text: str,
        k: int,
        rows: list,
        gem_model: str,
        gem_temp: float,
        max_docs: int,
        api_key: str | None,
    ) -> dict[str, Any]:
        if not rows:
            return {
                "data": [],
                "query": {"text": text, "k": k},
                "gemini": {
                    "answer": "No results found in the database for your query.",
                    "model": gem_model,
                    "temperature": gem_temp,
                },
            }

        docs = [self._coerce_doc_for_context(r) for r in rows]
        prompt = self._build_prompt(text, docs, max_docs=max_docs)
        gem_answer = self._call_gemini_safe(prompt, model=gem_model, temperature=gem_temp, api_key=api_key)
        return {
            "data": rows,
            "query": {"text": text, "k": k},
            "gemini": {"answer": gem_answer, "model": gem_model, "temperature": gem_temp},
        }

    async def _rows_from_qdrant(self, text: str, vector: list[float], k: int, api_key: str | None) -> list[dict]:
        from src.retrieval.qdrant_store import get_store

        store = get_store()
        size = store.owl_vector_size()
        if len(vector) != size:
            raw = await self._get_gemini_embedding(text, api_key=api_key, output_dimensionality=size)
            vector = self._l2_normalize(raw)
        return store.search_owl(vector, limit=k)

    async def ask_owl(
        self,
        text: str,
        k: int = 10,
        gemini_model: str | None = None,
        temperature: float | None = None,
        max_docs: int = 10,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        gem_model = gemini_model or self.default_model
        gem_temp = temperature if temperature is not None else self.default_temp

        # 1. Get Embedding from Gemini (Async/Lightweight)
        from src.retrieval.qdrant_store import backend_name

        requested = getattr(settings, "OWL_VECTOR_SIZE", None)
        output_dimensionality = (
            requested if isinstance(requested, int) and not isinstance(requested, bool) and requested > 0 else None
        )
        try:
            q_raw = await self._get_gemini_embedding(text, api_key=api_key, output_dimensionality=output_dimensionality)
            q = self._l2_normalize(q_raw)
        except Exception as e:
            return {"data": [], "query": {"text": text, "k": k}, "error": f"Embedding failed: {e}"}

        if backend_name(getattr(settings, "OWL_BACKEND", None), "postgres") == "qdrant":
            try:
                rows = await self._rows_from_qdrant(text, q, k, api_key)
            except Exception as e:
                logger.error(f"ask_owl failed: {e}")
                return {"data": [], "query": {"text": text, "k": k}, "error": str(e)}
            return self._response_from_rows(text, k, rows, gem_model, gem_temp, max_docs, api_key)

        # 2. Database Search
        conn = cur1 = cur2 = None
        try:
            conn = psycopg2.connect(
                host=settings.OWL_DB_HOST,
                port=settings.OWL_DB_PORT,
                user=settings.OWL_DB_USER,
                password=settings.OWL_DB_PASSWORD or settings.POSTGRESQL_PASS,
                dbname=settings.OWL_DB_NAME,
            )

            cur1 = conn.cursor(cursor_factory=RealDictCursor)
            # Optimized Cosine Similarity Query
            # Using multi-array unnest for performance if pgvector is missing
            sql_top = """
            WITH ref_vector AS ( SELECT %s::float8[] AS v )
            SELECT
              t.uuid,
              (SELECT SUM(a * b)
               FROM unnest(t.embedding, rv.v) AS x(a, b)
              ) AS cosine_similarity
            FROM vw_combined_report_data t, ref_vector rv
            ORDER BY cosine_similarity DESC NULLS LAST
            LIMIT %s;
            """
            cur1.execute(sql_top, (q, k))
            top_matches = cur1.fetchall()

            rows = []
            if top_matches:
                ordered = [
                    (r["uuid"], float(r["cosine_similarity"]))
                    for r in top_matches
                    if r.get("cosine_similarity") is not None
                ]

                if ordered:
                    values_clause = ",".join(["(%s,%s)"] * len(ordered))
                    params = []
                    for u, s in ordered:
                        params.extend([u, s])

                    cur2 = conn.cursor(cursor_factory=RealDictCursor)
                    sql_full = f"""
                        WITH ranked(uuid, sim) AS ( VALUES {values_clause} )
                        SELECT d.*, r.sim AS similarity
                        FROM ranked r
                        JOIN vw_combined_report_data d USING (uuid)
                        ORDER BY r.sim DESC;
                    """
                    cur2.execute(sql_full, params)
                    rows = cur2.fetchall()
                    for row in rows:
                        row.pop("embedding", None)

            return self._response_from_rows(text, k, rows, gem_model, gem_temp, max_docs, api_key)

        except Exception as e:
            logger.error(f"ask_owl failed: {e}")
            return {"data": [], "query": {"text": text, "k": k}, "error": str(e)}
        finally:
            if cur1:
                cur1.close()
            if cur2:
                cur2.close()
            if conn:
                conn.close()


owl_service = OwlService()
