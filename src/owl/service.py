import logging
import time
from typing import Any, Dict

import google.generativeai as genai
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from sentence_transformers import SentenceTransformer

from src.core.settings import settings

logger = logging.getLogger(__name__)

# Initialize model and Gemini
_embed_model = SentenceTransformer("all-MiniLM-L6-v2")

if settings.OWL_GOOGLE_API_KEY:
    genai.configure(api_key=settings.OWL_GOOGLE_API_KEY)

class OwlService:
    def __init__(self):
        self.default_model = "gemini-1.5-flash"
        self.default_temp = 0.5

    def _l2_normalize(self, vec: np.ndarray) -> np.ndarray:
        denom = np.linalg.norm(vec)
        if denom == 0.0 or not np.isfinite(denom):
            return vec
        return vec / denom

    def _coerce_doc_for_context(self, row: dict) -> dict:
        title = row.get("title") or row.get("report_title") or row.get("headline") or "Untitled"
        source = row.get("source") or row.get("publisher") or row.get("origin") or "Unknown"
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
            chunks.append(f"{meta}\n{d.get('combined_details','')}")
        context_block = "\n\n---\n\n".join(chunks) if chunks else "No context documents."
        return (
            f"{system_prompt}\n\n"
            f"### Context documents\n{context_block}\n\n"
            f"### User question\n{user_question}\n\n"
            f"### Your answer"
        )

    def _call_gemini_safe(self, prompt: str, model: str, temperature: float) -> str:
        try:
            if not settings.OWL_GOOGLE_API_KEY:
                return "⚠️ Gemini API key not configured."
            m = genai.GenerativeModel(model)
            resp = m.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=temperature),
            )
            return resp.text if hasattr(resp, "text") and resp.text else "⚠️ No response text from Gemini."
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            return f"⚠️ Gemini call failed: {e}"

    def ask_owl(self, text: str, k: int = 10, gemini_model: str | None = None, temperature: float | None = None, max_docs: int = 10) -> Dict[str, Any]:
        gem_model = gemini_model or self.default_model
        gem_temp = temperature if temperature is not None else self.default_temp

        # Encode + normalize query vector
        q_raw = _embed_model.encode(text)
        q_np = np.asarray(q_raw, dtype=np.float64)
        q = self._l2_normalize(q_np).tolist()


        conn = cur1 = cur2 = None
        try:
            conn = psycopg2.connect(
                host=settings.OWL_DB_HOST,
                port=settings.OWL_DB_PORT,
                user=settings.OWL_DB_USER,
                password=settings.OWL_DB_PASSWORD or settings.POSTGRESQL_PASS,
                dbname=settings.OWL_DB_NAME
            )
            time.sleep(0.1)

            cur1 = conn.cursor(cursor_factory=RealDictCursor)
            sql_top = """
            WITH ref_vector AS ( SELECT %s::float8[] AS v )
            SELECT
              t.uuid,
              (SELECT SUM(a * b)
                 FROM unnest(t.embedding) WITH ORDINALITY AS e(a, i)
                 JOIN unnest(rv.v)       WITH ORDINALITY AS q(b, j)
                   ON i = j
              ) AS cosine_similarity
            FROM vw_combined_report_data t, ref_vector rv
            ORDER BY cosine_similarity DESC NULLS LAST
            LIMIT %s;
            """
            cur1.execute(sql_top, (q, k))
            top_matches = cur1.fetchall()

            rows = []
            if top_matches:
                ordered = [(r["uuid"], float(r["cosine_similarity"])) for r in top_matches]
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

            # Gemini integration
            docs = [self._coerce_doc_for_context(r) for r in rows]
            prompt = self._build_prompt(text, docs, max_docs=max_docs)
            gem_answer = self._call_gemini_safe(prompt, model=gem_model, temperature=gem_temp)

            return {
                "data": rows,
                "query": {"text": text, "k": k},
                "gemini": {
                    "answer": gem_answer,
                    "model": gem_model,
                    "temperature": gem_temp
                }
            }

        except Exception as e:
            logger.error(f"ask_owl failed: {e}")
            return {
                "data": [],
                "query": {"text": text, "k": k},
                "error": str(e)
            }
        finally:
            if cur1: cur1.close()
            if cur2: cur2.close()
            if conn: conn.close()

owl_service = OwlService()
