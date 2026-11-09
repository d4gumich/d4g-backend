"""Serve the Lighthouse practice page at an unguessable path.

The page is not on the public website. GitHub Pages artifacts are public, so a
secret folder there would be listed for anyone who downloads the build. This
route lives on the API instead. The code is an environment value, never a
source file. A missing code, a short code, and a wrong code all answer 404
with the same body as any other missing route.
"""

from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from src.core.settings import settings

PAGE_ROOT = Path(__file__).resolve().parent / "practice_page"
_CODE_MIN = 32
_NOT_FOUND = "Not Found"

router = APIRouter(include_in_schema=False)


def practice_code_ok(code: str) -> bool:
    expected = settings.LIGHTHOUSE_DEV_PAGE_CODE or ""
    if len(expected) < _CODE_MIN or not isinstance(code, str):
        return False
    left = hashlib.sha256(code.encode("utf-8", "replace")).digest()
    right = hashlib.sha256(expected.encode("utf-8")).digest()
    return secrets.compare_digest(left, right)


def practice_file(asset_path: str) -> Path | None:
    relative = (asset_path or "").strip("/")
    if relative == "":
        relative = "index.html"
    if "\\" in relative or relative.split("/")[0] == "..":
        return None
    root = PAGE_ROOT.resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        return None
    if not candidate.is_file():
        return None
    return candidate


def _missing() -> HTTPException:
    return HTTPException(status_code=404, detail=_NOT_FOUND)


@router.get("/v1/products/lighthouse/d/{code}")
async def practice_page_root(code: str):
    if not practice_code_ok(code):
        raise _missing()
    return RedirectResponse(
        url=f"/api/v1/products/lighthouse/d/{code}/",
        status_code=307,
        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"},
    )


@router.get("/v1/products/lighthouse/d/{code}/{asset_path:path}")
async def practice_page_file(code: str, asset_path: str):
    if not practice_code_ok(code):
        raise _missing()
    target = practice_file(asset_path)
    if target is None:
        raise _missing()
    return FileResponse(
        target,
        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"},
    )
