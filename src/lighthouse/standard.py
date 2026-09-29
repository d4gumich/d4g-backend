import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

TOP_K = 3
COLLECTION_NAME = "career_rag"

EXTRACT_RULES = """Extract ONLY the skills explicitly mentioned in the resume.
Rules:
- Do NOT infer skills.
- Do NOT guess technologies.
- Do NOT repeat skills.
- If a skill is not written in the resume, do not include it.
Return ONLY a comma-separated list."""

RECOMMEND_RULES = (
    "You are a career advisor. Based on the candidate's skills and matching job roles, "
    "recommend 3 additional job titles they should consider. "
    "Return ONLY a numbered list of job titles with a one-sentence explanation each. No extra text."
)


class QdrantUnavailableError(RuntimeError):
    pass


class GeminiRejectedError(RuntimeError):
    pass


def parse_skills(raw: str) -> list[str]:
    line = (raw or "").split("\n")[0].strip()
    return list(dict.fromkeys(part.strip() for part in line.split(",") if part.strip()))


def parse_recommendation_lines(raw: str) -> list[str]:
    return [line.strip() for line in (raw or "").splitlines() if line.strip()]


def extract_prompt(resume_text: str) -> str:
    return f"{EXTRACT_RULES}\n\nResume:\n{resume_text}\n\nSkills:"


def recommend_prompt(skills: str, jobs: list[dict[str, Any]]) -> str:
    job_context = "\n".join(f"- {job['title']} (Skills: {job['skills']})" for job in jobs)
    return f"{RECOMMEND_RULES}\n\nCandidate Skills: {skills}\n\nTop Matching Jobs:\n{job_context}\n\nRecommendations:"


def query_career_rag(client: Any, collection: str, vector: list[float], limit: int = TOP_K) -> list[dict[str, Any]]:
    if not client.collection_exists(collection):
        raise QdrantUnavailableError("The career collection is not available.")
    result = client.query_points(collection_name=collection, query=vector, limit=limit, with_payload=True)
    jobs = []
    for hit in result.points:
        payload = hit.payload or {}
        jobs.append(
            {
                "title": payload.get("title") or "Untitled",
                "skills": payload.get("skills") or "",
                "description": payload.get("description") or "",
                "score": float(hit.score or 0),
            }
        )
    return jobs


def query_configured_collection(vector: list[float], limit: int = TOP_K) -> list[dict[str, Any]]:
    from src.core.settings import settings

    if not settings.QDRANT_URL:
        raise QdrantUnavailableError("Qdrant is not configured.")
    from qdrant_client import QdrantClient

    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY, timeout=10)
    collection = settings.QDRANT_COLLECTION or COLLECTION_NAME
    return query_career_rag(client, collection, vector, limit)


_embedder = None


def default_embed(text: str) -> list[float]:
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer("BAAI/bge-base-en-v1.5")
    vector = _embedder.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]
    return vector.tolist()


async def gemini_complete(prompt: str, api_key: str, model: str) -> str:
    from google import genai

    from src.shared.byok import redact_secret

    client = genai.Client(api_key=api_key)
    try:
        response = await client.aio.models.generate_content(model=model, contents=prompt)
    except Exception as exc:
        logger.warning("Gemini request failed: %s", redact_secret(str(exc), api_key))
        raise GeminiRejectedError("The model request was rejected.") from None
    return getattr(response, "text", None) or ""


async def run_standard_pipeline(
    resume_text: str,
    *,
    complete: Callable[[str], Awaitable[str]],
    embed: Callable[[str], list[float]],
    query_points: Callable[[list[float], int], list[dict[str, Any]]],
) -> dict[str, Any]:
    skills = parse_skills(await complete(extract_prompt(resume_text)))
    if not skills:
        jobs: list[dict[str, Any]] = []
        recommendations = ["No skills were written in the resume."]
    else:
        skill_text = ", ".join(skills)
        jobs = query_points(embed(skill_text), TOP_K)
        recommendations = parse_recommendation_lines(await complete(recommend_prompt(skill_text, jobs)))
    return {
        "extracted_skills": skills,
        "top_jobs": jobs,
        "recommendations": recommendations,
        "status": "success",
        "engine": "standard",
    }
