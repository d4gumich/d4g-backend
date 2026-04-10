"""

@author: XabUG47
"""

import warnings

import psycopg2
from cryptography.utils import CryptographyDeprecationWarning

warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)


import sys
import time
import traceback

import google.generativeai as genai
import numpy as np
from psycopg2.extras import RealDictCursor
from secret import my_keys
from sentence_transformers import SentenceTransformer

# ── Gemini config (can be overridden in query_body) ───────────────────────────
GOOGLE_API_KEY = my_keys()["OWL_Google_API_key"]
DEFAULT_MODEL = "gemini-1.5-flash"
DEFAULT_TEMP = 0.5

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ── Embedding model ───────────────────────────────────────────────────────────
_model = SentenceTransformer("all-MiniLM-L6-v2")


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    denom = np.linalg.norm(vec)
    if denom == 0.0 or not np.isfinite(denom):
        return vec
    return vec / denom


def _coerce_doc_for_context(row: dict) -> dict:
    title = row.get("title") or row.get("report_title") or row.get("headline") or "Untitled"
    source = row.get("source") or row.get("publisher") or row.get("origin") or "Unknown"
    page = row.get("page_label") or row.get("page") or row.get("page_no") or ""
    url = row.get("URL") or row.get("url") or row.get("link") or row.get("report_url") or ""
    body = row.get("combined_details") or row.get("document") or row.get("summary") or row.get("content") or ""
    return {"title": title, "source": source, "page_label": page, "URL": url, "combined_details": body}


def _build_prompt(user_question: str, docs: list, max_docs: int = 10) -> str:
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


def _call_gemini_safe(prompt: str, model: str, temperature: float) -> str:
    try:
        if not GOOGLE_API_KEY:
            return "⚠️ Gemini API key not configured."
        m = genai.GenerativeModel(model)
        resp = m.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=temperature),
        )
        return resp.text if hasattr(resp, "text") and resp.text else "⚠️ No response text from Gemini."
    except Exception as e:
        return f"⚠️ Gemini call failed: {e}"


def ask_owl(query_body: dict):
    """
    query_body: {
        "text": "...",
        "k": 10,
        "gemini_model": "gemini-1.5-pro",   # optional
        "temperature": 0.8,                 # optional
        "max_docs": 10                      # optional
    }
    """
    text = (query_body or {}).get("text")
    k = int((query_body or {}).get("k", 10))
    if not text or not isinstance(text, str):
        raise ValueError("query_body must include a 'text' string")
    if k <= 0:
        raise ValueError("'k' must be > 0")

    # Overrides
    gem_model = (query_body or {}).get("gemini_model", DEFAULT_MODEL)
    gem_temp = float((query_body or {}).get("temperature", DEFAULT_TEMP))
    max_docs = int((query_body or {}).get("max_docs", 10))

    # DB creds
    DB_HOST = "D4GUMSI-4679.postgres.pythonanywhere-services.com"
    DB_PORT = 14679
    DB_USER = "super"
    DB_NAME = "postgres"
    DB_PASSWORD = my_keys()["postgreSQL_pass"]

    # Encode + normalize query vector
    q = _model.encode(text)
    q = np.asarray(q, dtype=np.float64)
    q = _l2_normalize(q).tolist()

    # Let OS choose a free local port (avoid collisions)
    conn = cur1 = cur2 = None
    try:
        print("[DB] Connecting to Postgres...")
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME)

        # Small wait can help with some environments
        time.sleep(0.2)

        print("[DB] Connection successful.")

        # 1) Top-K similarity
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
        print(f"[DB] Retrieved {len(top_matches)} UUIDs.")

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
            print(f"[DB] Fetched {len(rows)} full rows.")
            for row in rows:
                row.pop("embedding", None)

        # 2) Gemini
        docs = [_coerce_doc_for_context(r) for r in rows]
        prompt = _build_prompt(text, docs, max_docs=max_docs)
        gem_answer = _call_gemini_safe(prompt, model=gem_model, temperature=gem_temp)

        return {
            "data": rows,
            "query": query_body,
            "gemini": {"answer": gem_answer, "model": gem_model, "temperature": gem_temp},
        }

    except Exception as e:
        print("[ERROR] ask_owl failed:")
        traceback.print_exc(file=sys.stdout)
        return {"data": [], "query": query_body, "error": str(e)}

    finally:
        # Close DB cursors/conn
        try:
            if cur1:
                cur1.close()
        except Exception:
            pass
        try:
            if cur2:
                cur2.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    import json

    print(
        'Enter JSON payload (e.g. {"text": "What are logistics challenges after a cyclone?", "k": 5, "gemini_model": "gemini-1.5-pro", "temperature": 0.7}):'
    )
    raw = input().strip()

    try:
        payload = json.loads(raw)
    except Exception as e:
        print(f"❌ Invalid JSON: {e}")
        exit(1)

    result = ask_owl(payload)
    # at the very bottom where you print the result:
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
