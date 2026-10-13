"""Product collections on Qdrant.

Owl and Chetah share one client and one cluster. Collection names are product
names. They do not encode an HTTP version or a Qdrant server version.

Creation sets a dense cosine vector or sparse IDF vectors and nothing else.
Quantization, memory tiers, and the turbo4 datatype are omitted so the same
call works on any Qdrant that supports sparse IDF.

Hangul classifies one uploaded PDF. It does not keep a search corpus, so it
has no collection here.
"""

from __future__ import annotations

import uuid
from typing import Any

from src.core.settings import settings

OWL_PRODUCT = "owl"
CHETAH_PRODUCT = "chetah"
PRODUCTS = (OWL_PRODUCT, CHETAH_PRODUCT)

# Named sparse channels inside the one Chetah collection. These are retrieval
# methods, not the v1/v2 HTTP routes. A later corpus adds a payload source and,
# when its vocabulary differs, another named vector. It does not add a collection.
CHETAH_SUMMARY = "summary"
CHETAH_LEX = "lex"
CHETAH_SOURCE_SUMMARY = "summary"
CHETAH_SOURCE_BM25F = "bm25f"
SCHEMA_VERSION = 1

_CHETAH_NAMESPACE = uuid.UUID("c3a1e5b2-7d44-5f18-9a60-2b8e4d17c091")


def backend_name(value: object, default: str) -> str:
    """Return a backend name. Non-strings (including test doubles) use the default."""
    if not isinstance(value, str) or not value.strip():
        return default
    return value.strip().lower()


def product_collections() -> dict[str, str]:
    return {
        OWL_PRODUCT: settings.OWL_COLLECTION,
        CHETAH_PRODUCT: settings.CHETAH_COLLECTION,
    }


def chetah_point_id(source: str, doc_id: object) -> str:
    """Stable UUID for one Chetah point. Integer ids from the two corpora overlap."""
    return str(uuid.uuid5(_CHETAH_NAMESPACE, f"chetah:{source}:{doc_id}"))


def owl_point_id(value: object) -> str | int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = str(value).strip()
    try:
        return str(uuid.UUID(text))
    except ValueError:
        pass
    if text.isdigit():
        return int(text)
    raise ValueError(f"Owl point id {text!r} is not a UUID or an integer")


def make_client():
    from qdrant_client import QdrantClient

    url = settings.QDRANT_URL
    if not isinstance(url, str) or not url.strip():
        raise RuntimeError("QDRANT_URL is not set")
    key = settings.QDRANT_API_KEY
    api_key = key.strip() if isinstance(key, str) and key.strip() else None
    return QdrantClient(url=url.strip(), api_key=api_key, timeout=30)


def _has_collection(client, name: str) -> bool:
    exists = getattr(client, "collection_exists", None)
    if callable(exists):
        return bool(exists(collection_name=name))
    found = client.get_collections().collections
    return any(item.name == name for item in found)


class QdrantStore:
    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = make_client()
        return self._client

    def ensure_owl_collection(self, size: int) -> None:
        from qdrant_client.http import models

        if size < 1:
            raise ValueError("Owl vector size must be positive")
        name = settings.OWL_COLLECTION
        if _has_collection(self.client, name):
            existing = self.owl_vector_size()
            if existing != size:
                raise ValueError(f"{name} stores {existing}-d vectors; this load has {size}-d vectors")
            return
        self.client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(size=size, distance=models.Distance.COSINE),
        )

    def ensure_chetah_collection(self) -> None:
        from qdrant_client.http import models

        name = settings.CHETAH_COLLECTION
        if not _has_collection(self.client, name):
            self.client.create_collection(
                collection_name=name,
                vectors_config={},
                sparse_vectors_config={
                    CHETAH_SUMMARY: models.SparseVectorParams(modifier=models.Modifier.IDF),
                    CHETAH_LEX: models.SparseVectorParams(modifier=models.Modifier.IDF),
                },
            )
        self._keyword_index(name, "source")

    def _keyword_index(self, collection_name: str, field_name: str) -> None:
        from qdrant_client.http import models

        try:
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise

    def owl_vector_size(self) -> int:
        info = self.client.get_collection(collection_name=settings.OWL_COLLECTION)
        vectors = info.config.params.vectors
        size = getattr(vectors, "size", None)
        if size is None and isinstance(vectors, dict) and vectors:
            first = next(iter(vectors.values()))
            size = first.get("size") if isinstance(first, dict) else getattr(first, "size", None)
        if not size:
            raise RuntimeError(f"{settings.OWL_COLLECTION} has no dense vector size")
        return int(size)

    def upsert(self, collection_name: str, points: list, batch_size: int = 64) -> int:
        written = 0
        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            self.client.upsert(collection_name=collection_name, points=batch, wait=True)
            written += len(batch)
        return written

    def search_owl(self, vector: list[float], limit: int) -> list[dict[str, Any]]:
        size = self.owl_vector_size()
        if len(vector) != size:
            raise ValueError(f"Query vector has {len(vector)} dimensions; {settings.OWL_COLLECTION} stores {size}")
        response = self.client.query_points(
            collection_name=settings.OWL_COLLECTION,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        rows = []
        for hit in response.points:
            row = dict(hit.payload or {})
            row.pop("embedding", None)
            row.pop("schema_version", None)
            row["uuid"] = str(hit.id)
            if hit.score is not None:
                row["similarity"] = float(hit.score)
            rows.append(row)
        return rows

    def search_chetah(self, vector_name: str, source: str, indices: list[int], limit: int = 10) -> list[dict[str, Any]]:
        from qdrant_client.http import models

        if not indices:
            return []
        ordered = sorted(set(indices))
        response = self.client.query_points(
            collection_name=settings.CHETAH_COLLECTION,
            query=models.SparseVector(indices=ordered, values=[1.0] * len(ordered)),
            using=vector_name,
            query_filter=models.Filter(
                must=[models.FieldCondition(key="source", match=models.MatchValue(value=source))]
            ),
            limit=limit,
            with_payload=True,
        )
        rows = []
        for hit in response.points:
            payload = dict(hit.payload or {})
            payload.pop("schema_version", None)
            payload.pop("source", None)
            rows.append(payload)
        return rows


_shared_store: QdrantStore | None = None


def get_store() -> QdrantStore:
    """One client per process. The first call reads QDRANT_URL."""
    global _shared_store
    if _shared_store is None:
        _shared_store = QdrantStore()
    return _shared_store
