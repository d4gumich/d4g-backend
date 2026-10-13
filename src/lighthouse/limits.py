from fastapi import HTTPException, UploadFile

MAX_RESUME_CHARS = 50_000
MAX_PDF_BYTES = 5_000_000
_READ_CHUNK = 1024 * 1024


async def read_capped_upload(file: UploadFile, limit: int) -> bytes:
    """Read an upload in chunks and stop once it passes the size cap."""
    chunks: list[bytes] = []
    total = 0
    while True:
        piece = await file.read(_READ_CHUNK)
        if not piece:
            break
        total += len(piece)
        if total > limit:
            raise HTTPException(status_code=413, detail="PDF is too large.")
        chunks.append(piece)
    return b"".join(chunks)
