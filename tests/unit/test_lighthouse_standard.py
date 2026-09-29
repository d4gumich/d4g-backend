import pytest

from src.lighthouse.standard import (
    QdrantUnavailableError,
    parse_recommendation_lines,
    parse_skills,
    query_career_rag,
    run_standard_pipeline,
)


def test_parse_skills_keeps_only_the_first_line_and_drops_duplicates():
    raw = "Python, SQL, Python, \nI inferred Kubernetes."
    assert parse_skills(raw) == ["Python", "SQL"]


def test_parse_recommendation_lines_drops_blank_lines():
    raw = "1. Data analyst\n\n2. Research assistant\n"
    assert parse_recommendation_lines(raw) == ["1. Data analyst", "2. Research assistant"]


class RecordingClient:
    def __init__(self, exists=True):
        self.exists = exists
        self.calls = []

    def collection_exists(self, name):
        self.calls.append(("exists", name))
        return self.exists

    def query_points(self, **kwargs):
        self.calls.append(("query", kwargs))

        class Hit:
            def __init__(self):
                self.score = 0.5
                self.payload = {"title": "Analyst", "skills": "SQL", "description": "Reports"}

        class Result:
            def __init__(self):
                self.points = [Hit()]

        return Result()

    def upsert(self, **kwargs):
        raise AssertionError("standard retrieval must not upsert")

    def create_collection(self, **kwargs):
        raise AssertionError("standard retrieval must not create a collection")


def test_query_career_rag_is_query_only():
    client = RecordingClient()
    jobs = query_career_rag(client, "career_rag", [0.1, 0.2], limit=3)
    assert jobs == [{"title": "Analyst", "skills": "SQL", "description": "Reports", "score": 0.5}]
    assert client.calls[0] == ("exists", "career_rag")
    assert client.calls[1][0] == "query"
    assert client.calls[1][1]["query"] == [0.1, 0.2]
    assert client.calls[1][1]["limit"] == 3


def test_missing_collection_does_not_create_one():
    client = RecordingClient(exists=False)
    with pytest.raises(QdrantUnavailableError):
        query_career_rag(client, "career_rag", [0.1], limit=3)
    assert [name for name, _ in client.calls] == ["exists"]


@pytest.mark.asyncio
async def test_pipeline_uses_the_same_instructions_and_injected_retrieval():
    prompts = []

    async def complete(prompt):
        prompts.append(prompt)
        if len(prompts) == 1:
            return "Python, SQL"
        return "1. Analyst\n2. Assistant"

    def embed(text):
        assert text == "Python, SQL"
        return [0.25, 0.75]

    def query_points(vector, limit):
        assert vector == [0.25, 0.75]
        assert limit == 3
        return [{"title": "Analyst", "skills": "SQL", "description": "Reports", "score": 0.25}]

    result = await run_standard_pipeline("Resume body", complete=complete, embed=embed, query_points=query_points)
    assert "Do NOT infer skills." in prompts[0]
    assert "Extract ONLY the skills explicitly mentioned" in prompts[0]
    assert "Resume body" in prompts[0]
    assert "career advisor" in prompts[1]
    assert "recommend 3 additional job titles" in prompts[1]
    assert result["extracted_skills"] == ["Python", "SQL"]
    assert result["top_jobs"][0]["title"] == "Analyst"
    assert result["recommendations"] == ["1. Analyst", "2. Assistant"]
    assert result["status"] == "success"
    assert result["engine"] == "standard"
