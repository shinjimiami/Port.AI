"""Supabase Storage service for fundamental analysis file uploads.

All file I/O for the fundamental analysis feature goes through here.
Files are stored under:  {bucket}/{user_id}/{analysis_id}/{filename}
"""
import logging
import mimetypes
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env"
            )
        from supabase import create_client
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _client


def _storage():
    return _get_client().storage.from_(settings.SUPABASE_BUCKET)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def upload_file(
    file_bytes: bytes,
    filename: str,
    user_id: int,
    analysis_id: int,
) -> dict:
    """Upload a file to Supabase Storage.

    Returns:
        {"storage_path": str, "public_url": str}
    """
    ext = Path(filename).suffix.lower()
    content_type = mimetypes.types_map.get(ext, "application/octet-stream")
    storage_path = f"{user_id}/{analysis_id}/{filename}"

    _storage().upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )

    # Build public URL (works for public buckets)
    public_url = (
        f"{settings.SUPABASE_URL}/storage/v1/object/public"
        f"/{settings.SUPABASE_BUCKET}/{storage_path}"
    )

    logger.info("Uploaded %s → %s", filename, storage_path)
    return {"storage_path": storage_path, "public_url": public_url}


def download_file(storage_path: str) -> bytes:
    """Download a file from Supabase Storage and return raw bytes."""
    response = _storage().download(storage_path)
    return response


def delete_file(storage_path: str) -> None:
    """Delete a single file from Supabase Storage."""
    _storage().remove([storage_path])
    logger.info("Deleted %s from storage", storage_path)


def delete_analysis_files(user_id: int, analysis_id: int) -> None:
    """Delete all files belonging to an analysis folder."""
    prefix = f"{user_id}/{analysis_id}/"
    try:
        items = _storage().list(prefix)
        paths = [f"{prefix}{item['name']}" for item in items]
        if paths:
            _storage().remove(paths)
            logger.info("Deleted %d files for analysis %d", len(paths), analysis_id)
    except Exception as exc:
        logger.warning("Could not delete analysis files: %s", exc)


def get_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    """Generate a signed (temporary) URL for private bucket access."""
    response = _storage().create_signed_url(storage_path, expires_in)
    return response.get("signedURL", "")


def is_configured() -> bool:
    """Return True if Supabase credentials are present."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY)
