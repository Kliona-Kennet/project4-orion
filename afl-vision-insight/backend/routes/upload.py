# routes/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from pathlib import Path
from datetime import datetime, timezone
import os, uuid, shutil

from backend.storage import save_upload  # Postgres-backed helper

router = APIRouter()

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))
CHUNK_SIZE = 1024 * 1024  # 1 MB

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
VIDEO_DIR = BASE_DIR / "uploaded_videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_MIME = {"video/mp4", "video/quicktime"}  # mp4 / mov
VIDEO_EXTS = {".mp4", ".mov"}


def _safe_ext(name: str) -> str:
    return Path(name).suffix.lower()


@router.post("/", summary="Upload video (mp4/mov only)")
async def upload_video(file: UploadFile = File(..., description="mp4/mov only")):
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="file is required",
        )

    ext = _safe_ext(file.filename)
    content_type = (file.content_type or "").lower()

    mime_ok = content_type in VIDEO_MIME if content_type else False
    ext_ok = ext in VIDEO_EXTS
    if not (mime_ok or ext_ok):
        raise HTTPException(status_code=400, detail="Only video files (.mp4, .mov) are accepted")

    # Generate ID + destination path
    file_id = uuid.uuid4().hex
    suffix = ext if ext_ok else ".mp4"
    dest_path = VIDEO_DIR / f"{file_id}{suffix}"

    # Stream to disk with size guard
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    written = 0
    try:
        with dest_path.open("wb") as out:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    out.close()
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail=f"file too large (> {MAX_UPLOAD_MB}MB)")
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()

    # Relative path stored in DB (relative to backend/ root)
    rel_path = f"uploaded_videos/{dest_path.name}"

    # Save to Postgres and return the DB record (includes id & created_at)
    rec = save_upload(path=rel_path, media_type="video", size_bytes=written)

    # If you prefer JSONResponse, keep it; otherwise returning `rec` is fine.
    return JSONResponse(
        {
            "id": rec["id"],
            "path": rec["path"],
            "media_type": rec["media_type"],
            "size_bytes": rec["size_bytes"],
            "created_at": rec["created_at"],
            # optionally echo original filename
            "original_filename": file.filename,
        }
    )
