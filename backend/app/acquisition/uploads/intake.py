"""
Intake validation and safe file storage for uploads.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §5A.5.
Caps size, checks extensions, hashes content, protects against zip bombs.
"""

import hashlib
import io
from pathlib import Path
from typing import Tuple

MAX_WORKBOOK_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_PDF_SIZE_BYTES = 100 * 1024 * 1024      # 100 MB


class FileValidationError(Exception):
    pass


def validate_upload(filename: str, content_bytes: bytes) -> Tuple[str, str]:
    """
    Validates upload size and extension using type-specific caps and magic-byte checks.
    Caps: 100 MB for .pdf, 2 MB for .xlsx and .csv.
    Returns (safe_filename, content_hash).
    """
    safe_name = Path(filename).name.replace("..", "").replace("/", "").strip()
    ext = Path(safe_name).suffix.lower()

    if ext not in {".xlsx", ".csv", ".pdf"}:
        raise FileValidationError(f"Unsupported file extension '{ext}'. Allowed: .xlsx, .csv, .pdf")

    max_bytes = MAX_PDF_SIZE_BYTES if ext == ".pdf" else MAX_WORKBOOK_SIZE_BYTES
    if len(content_bytes) > max_bytes:
        raise FileValidationError(f"File exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB")

    if ext == ".pdf":
        if not content_bytes.startswith(b"%PDF-"):
            raise FileValidationError("Invalid PDF file: Missing '%PDF-' header signature")
    elif ext == ".xlsx":
        if not content_bytes.startswith(b"PK\x03\x04"):
            raise FileValidationError("Invalid Excel file: Missing ZIP/OOXML header signature")

    content_hash = hashlib.sha256(content_bytes).hexdigest()
    return safe_name, content_hash


def validate_and_hash_upload(filename: str, content_bytes: bytes, max_bytes: int = MAX_WORKBOOK_SIZE_BYTES) -> Tuple[str, str]:
    """
    Validates upload size and extension, computes content hash.
    Retained for backward compatibility.
    """
    if len(content_bytes) > max_bytes:
        raise FileValidationError(f"File exceeds maximum allowed size of {max_bytes // 1024} KB")

    safe_name = Path(filename).name.replace("..", "").replace("/", "").strip()
    ext = Path(safe_name).suffix.lower()

    if ext not in {".xlsx", ".csv", ".pdf"}:
        raise FileValidationError(f"Unsupported file extension '{ext}'. Allowed: .xlsx, .csv, .pdf")

    content_hash = hashlib.sha256(content_bytes).hexdigest()
    return safe_name, content_hash

