"""Chetah term vectors for the one chetah_reports collection.

The summary channel stores term counts from the clustered CSV summaries.
The lex channel stores one weight per lemma: content term frequency plus
twice the metadata term frequency. Qdrant applies IDF at query time.
Length normalization from the in-process BM25F scorer is not reproduced.
The files backend remains the default until a shadow comparison is accepted.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from src.core.settings import settings
from src.retrieval.qdrant_store import (
    CHETAH_LEX,
    CHETAH_SOURCE_BM25F,
    CHETAH_SOURCE_SUMMARY,
    CHETAH_SUMMARY,
    SCHEMA_VERSION,
    chetah_point_id,
)

THEME_COLUMNS = (
    "Health",
    "Education",
    "Nutrition",
    "Protection",
    "Shelter",
    "Water, Sanitation and Hygiene",
    "Camp Coordination & Mgmt",
    "Early Recovery",
    "Emergency Telecom",
    "Food Security",
    "Humanitarian & Emergency Relief",
    "Logistics",
)

_summary_vectorizer: TfidfVectorizer | None = None
_term_ids: dict[str, int] | None = None


def dataset_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fit_summary_vectorizer(summaries: list[str]) -> TfidfVectorizer:
    """Vocabulary only. Counts stay raw so Qdrant can apply IDF later."""
    vectorizer = TfidfVectorizer(norm=None, smooth_idf=False, use_idf=False)
    vectorizer.fit(summaries)
    return vectorizer


def get_summary_vectorizer() -> TfidfVectorizer:
    global _summary_vectorizer
    if _summary_vectorizer is None:
        frame = pd.read_csv(dataset_root() / settings.CHETAH_DATASET_PATH)
        summaries = frame["summary"].fillna("").astype(str).tolist()
        _summary_vectorizer = fit_summary_vectorizer(summaries)
    return _summary_vectorizer


def summary_term_ids(query: str, vectorizer: TfidfVectorizer | None = None) -> list[int]:
    chosen = get_summary_vectorizer() if vectorizer is None else vectorizer
    row = chosen.transform([query or ""])
    return sorted({int(index) for index in row.indices})


def get_term_ids() -> dict[str, int]:
    """Lemma to term id. The posting lists stay on disk until a load."""
    global _term_ids
    if _term_ids is None:
        path = dataset_root() / settings.CHETAH_INV_PATH
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        _term_ids = {str(lemma): int(term_id) for lemma, term_id in payload["term_ids"].items()}
    return _term_ids


def bm25f_query_indices(query: str, term_ids: dict[str, int] | None = None) -> list[int]:
    from src.chetah.chetah_utils import lemmatize_string

    mapping = get_term_ids() if term_ids is None else term_ids
    found = []
    for token in lemmatize_string(query or ""):
        term_id = mapping.get(token)
        if term_id is not None:
            found.append(int(term_id))
    return sorted(set(found))


def bm25f_weights(inv: dict) -> dict[str, dict[int, float]]:
    """Walk postings once. Weight is content tf plus twice metadata tf."""
    by_doc: dict[str, dict[int, float]] = {}
    for term_key, posting in (inv.get("inv_index") or {}).items():
        term_id = int(term_key)
        fields = posting.get("fields") or {}
        content = fields.get("0") or {}
        meta = fields.get("1") or {}
        for doc_id in set(content) | set(meta):
            weight = float(content.get(doc_id) or 0) + 2.0 * float(meta.get(doc_id) or 0)
            if weight <= 0:
                continue
            by_doc.setdefault(str(doc_id), {})[term_id] = weight
    return by_doc


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value)


def _stable_id(value: object, fallback: object) -> str:
    if value is None or isinstance(value, bool):
        return str(fallback)
    if isinstance(value, float) and math.isnan(value):
        return str(fallback)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return str(fallback)
    return text


def _flag_on(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return False
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes"}


def _sparse_pairs(indices, values) -> tuple[list[int], list[float]]:
    merged: dict[int, float] = {}
    for index, value in zip(indices, values):
        key = int(index)
        merged[key] = merged.get(key, 0.0) + float(value)
    ordered = sorted(merged)
    return ordered, [merged[index] for index in ordered]


def build_summary_points(frame: pd.DataFrame, vectorizer: TfidfVectorizer | None = None) -> list:
    from qdrant_client.http import models

    summaries = frame["summary"].fillna("").astype(str)
    chosen = fit_summary_vectorizer(summaries.tolist()) if vectorizer is None else vectorizer
    matrix = chosen.transform(summaries.tolist())
    points = []
    for row_i, record in enumerate(frame.to_dict(orient="records")):
        sparse = matrix.getrow(row_i)
        if sparse.nnz == 0:
            continue
        indices, values = _sparse_pairs(sparse.indices, sparse.data)
        summary = _text(record.get("summary"))
        themes = [name for name in THEME_COLUMNS if _flag_on(record.get(name))]
        payload = {
            "schema_version": SCHEMA_VERSION,
            "source": CHETAH_SOURCE_SUMMARY,
            "doc_id": _stable_id(record.get("ID"), row_i),
            "title": _text(record.get("Title")),
            "date": _text(record.get("Date")),
            "link": _text(record.get("URL")),
            "cluster": _text(record.get("cluster")),
            "summary_short": summary[:450],
            "summary_full": summary,
            "organization": _text(record.get("Organization")),
            "themes": themes,
            "content": _text(record.get("Content")),
        }
        points.append(
            models.PointStruct(
                id=chetah_point_id(CHETAH_SOURCE_SUMMARY, payload["doc_id"]),
                vector={CHETAH_SUMMARY: models.SparseVector(indices=indices, values=values)},
                payload=payload,
            )
        )
    return points


def build_bm25f_points(inv: dict, docs: dict) -> list:
    from qdrant_client.http import models

    weights = bm25f_weights(inv)
    points = []
    for doc_id, record in docs.items():
        doc_weights = weights.get(str(doc_id))
        if not doc_weights:
            continue
        indices = sorted(doc_weights)
        values = [float(doc_weights[index]) for index in indices]
        payload = dict(record)
        payload["schema_version"] = SCHEMA_VERSION
        payload["source"] = CHETAH_SOURCE_BM25F
        payload["doc_id"] = str(doc_id)
        points.append(
            models.PointStruct(
                id=chetah_point_id(CHETAH_SOURCE_BM25F, doc_id),
                vector={CHETAH_LEX: models.SparseVector(indices=indices, values=values)},
                payload=payload,
            )
        )
    return points


def load_chetah_points() -> tuple[list, list]:
    """Read the CSV and both JSON files. Does not open Qdrant or Postgres."""
    frame = pd.read_csv(dataset_root() / settings.CHETAH_DATASET_PATH)
    summaries = frame["summary"].fillna("").astype(str).tolist()
    summary_points = build_summary_points(frame, fit_summary_vectorizer(summaries))
    with (dataset_root() / settings.CHETAH_INV_PATH).open(encoding="utf-8") as handle:
        inv = json.load(handle)
    with (dataset_root() / settings.CHETAH_DOC_PATH).open(encoding="utf-8") as handle:
        docs = json.load(handle)
    return summary_points, build_bm25f_points(inv, docs)
