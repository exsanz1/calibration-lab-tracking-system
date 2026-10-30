from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile

BASE_STORAGE_DIR = Path("storage/uploads")
WORKSHEET_DIR = BASE_STORAGE_DIR / "worksheets"
CERTIFICATE_DIR = BASE_STORAGE_DIR / "certificates"

ALLOWED_WORKSHEET_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".csv"}
ALLOWED_CERTIFICATE_EXTENSIONS = {".pdf"}


def init_storage() -> None:
    """Ensure storage directories exist."""
    WORKSHEET_DIR.mkdir(parents=True, exist_ok=True)
    CERTIFICATE_DIR.mkdir(parents=True, exist_ok=True)


def save_worksheet(qr_tag: str, file: UploadFile) -> str:
    """Save an uploaded worksheet file and return the saved path."""
    init_storage()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_WORKSHEET_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid worksheet format ({ext}). Supported: .xlsx, .xls, .xlsm, .csv",
        )

    safe_tag = qr_tag.replace("/", "_").replace(" ", "_")
    safe_name = f"{safe_tag}_worksheet{ext}"
    target_path = WORKSHEET_DIR / safe_name

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return str(target_path).replace("\\", "/")


def save_certificate(qr_tag: str, file: UploadFile) -> str:
    """Save an uploaded signed certificate file and return the saved path."""
    init_storage()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_CERTIFICATE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid certificate format ({ext}). Supported: .pdf only",
        )

    safe_tag = qr_tag.replace("/", "_").replace(" ", "_")
    safe_name = f"{safe_tag}_cert{ext}"
    target_path = CERTIFICATE_DIR / safe_name

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return str(target_path).replace("\\", "/")

