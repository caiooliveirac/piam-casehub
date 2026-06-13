"""File storage for Telegram attachments — persistent dir, sanitized names."""

from __future__ import annotations

import os
import re
import unicodedata

from app.config import settings

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str | None, default: str = "file") -> str:
    """Return a filesystem-safe filename with no path separators."""
    if not name:
        return default
    # Strip any directory components and normalise unicode.
    name = os.path.basename(name)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = _SAFE_CHARS.sub("_", name).strip("._")
    return name or default


def classify_attachment(mime_type: str | None, file_name: str | None) -> str:
    """Heuristic mapping to an attachment_type bucket."""
    mime = (mime_type or "").lower()
    name = (file_name or "").lower()
    if mime.startswith("image/"):
        return "ecg_image"
    if mime == "application/pdf" or name.endswith(".pdf"):
        return "ecg_pdf"
    if mime.startswith("application/") or mime.startswith("text/"):
        return "clinical_document"
    return "other"


def build_storage_path(case_public_id: str, file_name: str) -> str:
    """Compute (and ensure) the on-disk path for a case attachment."""
    case_dir = os.path.join(settings.upload_dir, case_public_id)
    os.makedirs(case_dir, exist_ok=True)
    return os.path.join(case_dir, sanitize_filename(file_name))


async def save_bytes(case_public_id: str, file_name: str, data: bytes) -> str:
    """Persist raw bytes and return the storage path."""
    path = build_storage_path(case_public_id, file_name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path
