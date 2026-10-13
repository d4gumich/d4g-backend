"""Load product collections into Qdrant.

Creates owl_reports and chetah_reports when asked. Names are products, not
API versions and not Qdrant server versions. Hangul classifies one uploaded
PDF and does not keep a search corpus, so this script creates no Hangul
collection.

Owl is read from a local JSONL file. This script does not connect to Postgres
and does not print the cluster URL or the API key. One object per line:

    {"id": "<uuid-or-integer>", "vector": [0.1, 0.2], "payload": {"title": "Report"}}

The first vector's length is the collection size. A later line with a
different length stops the load. Put embeddings in vector, not in payload.
Stored vectors are written as exported. The query path normalizes the question.

Export the Owl view through an SSH tunnel, write the JSONL on this machine,
then run the loader. Leave OWL_BACKEND and CHETAH_BACKEND at their defaults
until a shadow comparison has passed.

    ssh -L 14679:D4GUMSI-4679.postgres.pythonanywhere-services.com:14679 USER@ssh.pythonanywhere.com
    uv run python scripts/load_qdrant.py --owl-jsonl exports/owl.jsonl
    uv run python scripts/load_qdrant.py --chetah

Rerunning replaces points with the same ids.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def read_owl_jsonl(path: Path) -> tuple[int, list]:
    from qdrant_client.http import models

    from src.retrieval.qdrant_store import SCHEMA_VERSION, owl_point_id

    points = []
    size = None
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            obj = json.loads(text)
            vector = obj.get("vector")
            if not isinstance(vector, list) or not vector:
                raise ValueError(f"line {line_no}: vector must be a non-empty list")
            if size is None:
                size = len(vector)
            elif len(vector) != size:
                raise ValueError(f"line {line_no}: vector length {len(vector)} does not match {size}")
            raw_id = obj.get("id", obj.get("uuid"))
            if raw_id is None:
                raise ValueError(f"line {line_no}: id is required")
            raw_payload = obj.get("payload") or {}
            if not isinstance(raw_payload, dict):
                raise ValueError(f"line {line_no}: payload must be an object")
            payload = dict(raw_payload)
            payload.pop("embedding", None)
            payload.setdefault("schema_version", SCHEMA_VERSION)
            points.append(
                models.PointStruct(
                    id=owl_point_id(raw_id),
                    vector=[float(value) for value in vector],
                    payload=payload,
                )
            )
    if size is None:
        raise ValueError(f"{path} has no vectors")
    return size, points


def main(argv: list[str] | None = None) -> int:
    from src.core.settings import settings
    from src.retrieval.chetah_terms import load_chetah_points
    from src.retrieval.qdrant_store import QdrantStore

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chetah", action="store_true", help="Load both Chetah corpora into chetah_reports")
    parser.add_argument("--owl-jsonl", type=Path, help="Load an Owl JSONL export into owl_reports")
    args = parser.parse_args(argv)
    if not args.chetah and args.owl_jsonl is None:
        parser.error("Pass --chetah, --owl-jsonl, or both.")

    store = QdrantStore()
    if args.owl_jsonl is not None:
        size, points = read_owl_jsonl(args.owl_jsonl)
        store.ensure_owl_collection(size)
        written = store.upsert(settings.OWL_COLLECTION, points, batch_size=32)
        print(f"{settings.OWL_COLLECTION}: {written} points, {size} dimensions")
    if args.chetah:
        summary_points, lex_points = load_chetah_points()
        store.ensure_chetah_collection()
        summary_n = store.upsert(settings.CHETAH_COLLECTION, summary_points)
        lex_n = store.upsert(settings.CHETAH_COLLECTION, lex_points)
        print(f"{settings.CHETAH_COLLECTION}: {summary_n} summary points, {lex_n} lex points")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
