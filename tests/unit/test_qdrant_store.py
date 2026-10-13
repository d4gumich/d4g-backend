import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest
from qdrant_client.http import models

from scripts.load_qdrant import main as load_main
from scripts.load_qdrant import read_owl_jsonl
from src.chetah.service import search_v1, search_v2
from src.core.settings import settings
from src.owl.service import OwlService
from src.retrieval.chetah_terms import (
    bm25f_query_indices,
    bm25f_weights,
    build_bm25f_points,
    build_summary_points,
    fit_summary_vectorizer,
)
from src.retrieval.qdrant_store import (
    CHETAH_LEX,
    CHETAH_SOURCE_BM25F,
    CHETAH_SUMMARY,
    QdrantStore,
    backend_name,
    chetah_point_id,
    owl_point_id,
    product_collections,
)


class Hit:
    def __init__(self, point_id, score, payload):
        self.id = point_id
        self.score = score
        self.payload = payload


class FakeClient:
    def __init__(self):
        self.created = []
        self.indexes = []
        self.queries = []
        self.hits = []
        self.index_error = None
        self._sizes = {}

    def collection_exists(self, collection_name):
        return collection_name in self._sizes

    def create_collection(self, **kwargs):
        self.created.append(kwargs)
        vectors = kwargs.get("vectors_config")
        size = getattr(vectors, "size", None)
        if size:
            self._sizes[kwargs["collection_name"]] = size
        else:
            self._sizes.setdefault(kwargs["collection_name"], 0)

    def get_collection(self, collection_name):
        size = self._sizes[collection_name]
        vectors = SimpleNamespace(size=size)
        return SimpleNamespace(config=SimpleNamespace(params=SimpleNamespace(vectors=vectors)))

    def create_payload_index(self, **kwargs):
        if self.index_error is not None:
            raise self.index_error
        self.indexes.append(kwargs)

    def query_points(self, **kwargs):
        self.queries.append(kwargs)
        return SimpleNamespace(points=self.hits)

    def upsert(self, **kwargs):
        return kwargs


@pytest.fixture
def collection_names(monkeypatch):
    monkeypatch.setattr(settings, "OWL_COLLECTION", "owl_reports")
    monkeypatch.setattr(settings, "CHETAH_COLLECTION", "chetah_reports")


def test_backend_name_ignores_doubles_and_blanks():
    assert backend_name(MagicMock(), "postgres") == "postgres"
    assert backend_name(None, "files") == "files"
    assert backend_name("  ", "files") == "files"
    assert backend_name("  Qdrant ", "files") == "qdrant"


def test_product_collections_are_owl_and_chetah(collection_names):
    found = product_collections()
    assert set(found) == {"owl", "chetah"}
    assert "hangul" not in found
    assert found["owl"] == "owl_reports"
    assert found["chetah"] == "chetah_reports"


def test_point_ids_do_not_collide_across_chetah_corpora():
    assert chetah_point_id("summary", 3) == chetah_point_id("summary", "3")
    assert chetah_point_id("summary", 3) != chetah_point_id("bm25f", 3)
    assert owl_point_id(3) == 3
    assert owl_point_id("3") == 3
    assert owl_point_id("6b1e0c2a-8f4e-4c2a-9d1b-0a7c6e5f4d3b") == "6b1e0c2a-8f4e-4c2a-9d1b-0a7c6e5f4d3b"
    with pytest.raises(ValueError):
        owl_point_id(True)
    with pytest.raises(ValueError):
        owl_point_id("not-an-id")


def test_owl_collection_is_plain_cosine(collection_names):
    client = FakeClient()
    store = QdrantStore(client)
    store.ensure_owl_collection(8)
    store.ensure_owl_collection(8)
    assert len(client.created) == 1
    created = client.created[0]
    assert created["collection_name"] == "owl_reports"
    assert "quantization_config" not in created
    assert "hnsw_config" not in created
    assert created["vectors_config"].size == 8
    assert created["vectors_config"].distance == models.Distance.COSINE
    with pytest.raises(ValueError, match="8-d"):
        store.ensure_owl_collection(4)
    with pytest.raises(ValueError):
        store.ensure_owl_collection(0)


def test_chetah_collection_is_sparse_idf_without_quantization(collection_names):
    client = FakeClient()
    store = QdrantStore(client)
    store.ensure_chetah_collection()
    store.ensure_chetah_collection()
    assert len(client.created) == 1
    created = client.created[0]
    assert created["vectors_config"] == {}
    assert "quantization_config" not in created
    assert set(created["sparse_vectors_config"]) == {CHETAH_SUMMARY, CHETAH_LEX}
    for params in created["sparse_vectors_config"].values():
        assert params.modifier == models.Modifier.IDF
    assert client.indexes[0]["field_name"] == "source"
    assert client.indexes[0]["field_schema"] == models.PayloadSchemaType.KEYWORD

    client.index_error = RuntimeError("payload index already exists")
    store.ensure_chetah_collection()

    client.index_error = RuntimeError("connection refused")
    with pytest.raises(RuntimeError, match="connection refused"):
        store.ensure_chetah_collection()


def test_search_owl_strips_vectors_and_checks_size(collection_names):
    client = FakeClient()
    client._sizes["owl_reports"] = 2
    client.hits = [
        Hit(
            "6b1e0c2a-8f4e-4c2a-9d1b-0a7c6e5f4d3b",
            0.9,
            {"title": "A", "embedding": [1, 2], "schema_version": 1},
        )
    ]
    store = QdrantStore(client)
    rows = store.search_owl([0.0, 1.0], limit=4)
    assert rows == [{"title": "A", "uuid": "6b1e0c2a-8f4e-4c2a-9d1b-0a7c6e5f4d3b", "similarity": 0.9}]
    with pytest.raises(ValueError, match="dimensions"):
        store.search_owl([1.0], limit=1)
    assert len(client.queries) == 1


def test_search_chetah_filters_source_and_sorts_terms(collection_names):
    client = FakeClient()
    client.hits = [Hit("point", 0.2, {"source": "bm25f", "schema_version": 1, "report_title": ["A"]})]
    store = QdrantStore(client)
    assert store.search_chetah(CHETAH_LEX, CHETAH_SOURCE_BM25F, []) == []
    assert client.queries == []

    rows = store.search_chetah(CHETAH_LEX, CHETAH_SOURCE_BM25F, [3, 1, 3], limit=10)
    assert rows == [{"report_title": ["A"]}]
    query = client.queries[0]
    assert query["using"] == CHETAH_LEX
    assert query["collection_name"] == "chetah_reports"
    assert list(query["query"].indices) == [1, 3]
    assert list(query["query"].values) == [1.0, 1.0]
    condition = query["query_filter"].must[0]
    assert condition.key == "source"
    assert condition.match.value == CHETAH_SOURCE_BM25F


def test_summary_points_keep_counts_themes_and_stable_ids():
    frame = pd.DataFrame(
        [
            {
                "ID": 3,
                "Content": "full body",
                "summary": "flood shelter",
                "Title": "Flood",
                "Organization": "IFRC",
                "URL": "http://example.test/a",
                "cluster": "2",
                "Health": 0,
                "Shelter": 1,
                "Date": "2020-01-02",
            },
            {
                "ID": 4,
                "Content": "",
                "summary": "",
                "Title": "Empty",
                "Organization": "",
                "URL": "",
                "cluster": "",
                "Date": "",
            },
        ]
    )
    points = build_summary_points(frame, fit_summary_vectorizer(["flood shelter", ""]))
    assert len(points) == 1
    point = points[0]
    assert point.id == chetah_point_id("summary", 3)
    assert point.payload["themes"] == ["Shelter"]
    assert point.payload["source"] == "summary"
    assert point.payload["title"] == "Flood"
    assert "embedding" not in point.payload
    sparse = point.vector[CHETAH_SUMMARY]
    assert list(sparse.indices) == sorted(sparse.indices)
    assert sparse.values


def test_bm25f_weights_walk_postings_once():
    inv = {
        "inv_index": {
            "0": {"df": 1, "fields": {"0": {"7": 3}, "1": {"7": 1}}},
            "2": {"df": 1, "fields": {"0": {"7": 1, "8": 4}, "1": {}}},
        }
    }
    weights = bm25f_weights(inv)
    assert weights["7"][0] == 5
    assert weights["7"][2] == 1
    assert weights["8"][2] == 4

    points = build_bm25f_points(inv, {"7": {"report_title": ["Shelter note"], "summary": "s"}, "9": {}})
    assert len(points) == 1
    assert points[0].id == chetah_point_id("bm25f", "7")
    assert points[0].id != chetah_point_id("summary", "7")
    assert list(points[0].vector[CHETAH_LEX].indices) == [0, 2]
    assert list(points[0].vector[CHETAH_LEX].values) == [5.0, 1.0]
    assert points[0].payload["report_title"] == ["Shelter note"]
    assert points[0].payload["source"] == "bm25f"


def test_bm25f_query_indices_drop_unknown_terms(monkeypatch):
    monkeypatch.setattr("src.chetah.chetah_utils.lemmatize_string", lambda text: ["flood", "missing", "flood"])
    assert bm25f_query_indices("flood", {"flood": 4, "shelter": 2}) == [4]


def test_search_v1_qdrant_skips_the_csv(monkeypatch):
    monkeypatch.setattr(settings, "CHETAH_BACKEND", "qdrant")

    def boom():
        raise AssertionError("csv loaded")

    monkeypatch.setattr("src.chetah.service.get_chetah_v1_data", boom)
    monkeypatch.setattr("src.retrieval.chetah_terms.summary_term_ids", lambda query: [3, 1])
    seen: dict[str, object] = {}

    class Store:
        def search_chetah(self, vector_name, source, indices, limit=10):
            seen["args"] = (vector_name, source, indices, limit)
            return [
                {
                    "title": "T",
                    "date": "2020-01-01",
                    "link": "http://example.test",
                    "cluster": "1",
                    "summary_short": "short",
                    "summary_full": "full text",
                    "content": "hidden",
                }
            ]

    monkeypatch.setattr("src.retrieval.qdrant_store.get_store", Store)
    assert search_v1("flood") == [
        {
            "title": "T",
            "date": "2020-01-01",
            "link": "http://example.test",
            "cluster": "1",
            "summary_short": "short",
            "summary_full": "full text",
        }
    ]
    assert seen["args"] == (CHETAH_SUMMARY, "summary", [3, 1], 10)


def test_unknown_chetah_backend_keeps_the_file_index(monkeypatch):
    monkeypatch.setattr(settings, "CHETAH_BACKEND", "legacy")
    monkeypatch.setattr("src.chetah.service.get_chetah_v1_data", lambda: (None, None, None))
    assert search_v1("flood") == []


def test_search_v2_qdrant_skips_doc_table(monkeypatch):
    monkeypatch.setattr(settings, "CHETAH_BACKEND", "qdrant")

    def boom():
        raise AssertionError("doc table loaded")

    monkeypatch.setattr("src.chetah.service.get_chetah_v2_data", boom)
    monkeypatch.setattr("src.retrieval.chetah_terms.bm25f_query_indices", lambda query: [4])

    class Store:
        def search_chetah(self, vector_name, source, indices, limit=10):
            assert (vector_name, source, indices, limit) == (CHETAH_LEX, CHETAH_SOURCE_BM25F, [4], 10)
            return [{"report_title": ["Note"], "summary": "body"}]

    monkeypatch.setattr("src.retrieval.qdrant_store.get_store", Store)
    assert search_v2("flood") == [{"report_title": ["Note"], "summary": "body"}]
    assert search_v2("") == []


@pytest.mark.asyncio
async def test_ask_owl_qdrant_normalizes_and_skips_postgres(monkeypatch):
    monkeypatch.setattr(settings, "OWL_BACKEND", "qdrant")
    monkeypatch.setattr(settings, "OWL_VECTOR_SIZE", None)
    monkeypatch.setattr(
        "src.owl.service.psycopg2.connect",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("postgres")),
    )
    service = OwlService()
    calls = []

    async def embed(text, api_key=None, output_dimensionality=None):
        calls.append(output_dimensionality)
        return [0.0, 3.0, 4.0]

    monkeypatch.setattr(service, "_get_gemini_embedding", embed)
    monkeypatch.setattr(service, "_call_gemini_safe", lambda *args, **kwargs: "from qdrant")
    seen: dict[str, object] = {}

    class Store:
        def owl_vector_size(self):
            return 3

        def search_owl(self, vector, limit):
            seen["vector"] = vector
            seen["limit"] = limit
            return [{"uuid": "abc", "title": "Report", "combined_details": "body", "similarity": 0.4}]

    monkeypatch.setattr("src.retrieval.qdrant_store.get_store", Store)
    result = await service.ask_owl("help", k=2, api_key="k")
    assert calls == [None]
    assert result["gemini"]["answer"] == "from qdrant"
    assert result["data"][0]["title"] == "Report"
    assert seen["limit"] == 2
    assert seen["vector"] == pytest.approx([0.0, 0.6, 0.8])


@pytest.mark.asyncio
async def test_ask_owl_reembeds_when_the_collection_size_differs(monkeypatch):
    monkeypatch.setattr(settings, "OWL_BACKEND", "qdrant")
    monkeypatch.setattr(settings, "OWL_VECTOR_SIZE", None)
    service = OwlService()
    calls = []

    async def embed(text, api_key=None, output_dimensionality=None):
        calls.append(output_dimensionality)
        if output_dimensionality == 2:
            return [3.0, 4.0]
        return [1.0, 0.0, 0.0]

    monkeypatch.setattr(service, "_get_gemini_embedding", embed)
    monkeypatch.setattr(service, "_call_gemini_safe", lambda *args, **kwargs: "resized")
    seen: dict[str, object] = {}

    class Store:
        def owl_vector_size(self):
            return 2

        def search_owl(self, vector, limit):
            seen["vector"] = vector
            return [{"uuid": "abc", "title": "T", "combined_details": "c", "similarity": 1}]

    monkeypatch.setattr("src.retrieval.qdrant_store.get_store", Store)
    result = await service.ask_owl("help", api_key="k")
    assert calls == [None, 2]
    assert seen["vector"] == pytest.approx([0.6, 0.8])
    assert result["gemini"]["answer"] == "resized"


@pytest.mark.asyncio
async def test_ask_owl_qdrant_error_stays_off_postgres(monkeypatch):
    monkeypatch.setattr(settings, "OWL_BACKEND", "qdrant")
    monkeypatch.setattr(settings, "OWL_VECTOR_SIZE", None)
    monkeypatch.setattr(
        "src.owl.service.psycopg2.connect",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("postgres")),
    )
    service = OwlService()

    async def embed(text, api_key=None, output_dimensionality=None):
        return [1.0, 0.0]

    monkeypatch.setattr(service, "_get_gemini_embedding", embed)

    class Store:
        def owl_vector_size(self):
            raise RuntimeError("collection missing")

    monkeypatch.setattr("src.retrieval.qdrant_store.get_store", Store)
    result = await service.ask_owl("help", api_key="k")
    assert result["data"] == []
    assert "collection missing" in result["error"]


def test_read_owl_jsonl_strips_embeddings(tmp_path):
    path = tmp_path / "owl.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "6b1e0c2a-8f4e-4c2a-9d1b-0a7c6e5f4d3b",
                        "vector": [1, 0],
                        "payload": {"title": "A", "embedding": [9, 9]},
                    }
                ),
                json.dumps({"uuid": 7, "vector": [0, 1], "payload": {"title": "B"}}),
                "",
            ]
        ),
        encoding="utf-8",
    )
    size, points = read_owl_jsonl(path)
    assert size == 2
    assert points[0].payload["title"] == "A"
    assert "embedding" not in points[0].payload
    assert points[0].payload["schema_version"] == 1
    assert points[1].id == 7

    mismatch = tmp_path / "bad.jsonl"
    mismatch.write_text(
        json.dumps({"id": 1, "vector": [1, 0]}) + "\n" + json.dumps({"id": 2, "vector": [1]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not match"):
        read_owl_jsonl(mismatch)

    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="no vectors"):
        read_owl_jsonl(empty)


def test_loader_requires_a_target():
    with pytest.raises(SystemExit):
        load_main([])
