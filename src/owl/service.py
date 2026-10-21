import logging
from typing import Any

import numpy as np
import psycopg
from psycopg.rows import dict_row

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

    async def _get_gemini_embedding(self, text: str, api_key: str | None = None) -> list[float]:
        """Uses the Gemini API to get text embeddings, removing the need for local heavy models."""
        from google import genai

        try:
            key = api_key or settings.GOOGLE_API_KEY
            if not key:
                raise ValueError("Google API key not configured for embeddings.")

            client = genai.Client(api_key=key)
            # Standard embedding call with modern SDK
            result = client.models.embed_content(
                model=self.embed_model, contents=text, config={"task_type": "RETRIEVAL_QUERY"}
            )
            # google-genai returns a list of embeddings
            return result.embeddings[0].values
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

    def _query_database_sync(self, q: list[float], k: int) -> list[dict[str, Any]]:
        # Single database query to find matching items and compute cosine similarity
        sql = """
        WITH ref_vector AS ( SELECT %s::float8[] AS v )
        SELECT
          t.*,
          (SELECT SUM(a * b)
           FROM unnest(t.embedding, rv.v) AS x(a, b)
          ) AS similarity
        FROM vw_combined_report_data t, ref_vector rv
        ORDER BY similarity DESC NULLS LAST
        LIMIT %s;
        """
        with psycopg.connect(
            host=settings.OWL_DB_HOST,
            port=settings.OWL_DB_PORT,
            user=settings.OWL_DB_USER,
            password=settings.OWL_DB_PASSWORD or settings.POSTGRESQL_PASS,
            dbname=settings.OWL_DB_NAME,
            row_factory=dict_row,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (q, k))
                rows = cur.fetchall()
                # Remove embedding arrays from returned rows to save space and serialize clean responses
                for r in rows:
                    r.pop("embedding", None)
                return rows

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
        try:
            q_raw = await self._get_gemini_embedding(text, api_key=api_key)
            q = self._l2_normalize(q_raw)
        except Exception as e:
            return {"data": [], "query": {"text": text, "k": k}, "error": f"Embedding failed: {e}"}

        # 2. Database Search (Offloaded to thread pool to avoid blocking ASGI event loop)
        try:
            from anyio.to_thread import run_sync

            rows = await run_sync(self._query_database_sync, q, k)

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

        except Exception as e:
            logger.error(f"ask_owl failed: {e}")
            return {"data": [], "query": {"text": text, "k": k}, "error": str(e)}


owl_service = OwlService()
