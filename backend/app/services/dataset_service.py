import json
import uuid
from pathlib import Path

import pandas as pd
from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def _extension(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    if len(parts) != 2:
        return ""
    return parts[1].lower()


def list_sheets(path: Path, file_type: str) -> list[str]:
    """Returns sheet names for an Excel file, or [] for CSV (no sheet concept)."""
    if file_type == "csv":
        return []
    try:
        # Must close explicitly: ExcelFile keeps the file handle open (unlike
        # pd.read_excel, which closes it after reading), and on Windows an open
        # handle blocks the caller's cleanup unlink() on error paths.
        with pd.ExcelFile(path, engine="openpyxl" if file_type == "xlsx" else None) as book:
            return list(book.sheet_names)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read workbook: {exc}") from exc


def read_dataframe(path: Path, file_type: str, sheet_name: str | None = None) -> pd.DataFrame:
    try:
        if file_type == "csv":
            return pd.read_csv(path)
        return pd.read_excel(
            path, sheet_name=sheet_name or 0, engine="openpyxl" if file_type == "xlsx" else None
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse dataset file: {exc}") from exc


def save_upload(project_id: int, file: UploadFile) -> tuple[Path, str, str]:
    """Validates and persists the raw upload. Returns (stored_path, file_type, original_filename)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file has no filename.")

    file_type = _extension(file.filename)
    if file_type not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{file_type}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
        )

    project_dir = Path(settings.upload_dir) / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}.{file_type}"
    stored_path = project_dir / stored_name

    size = 0
    with open(stored_path, "wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                stored_path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="File exceeds the 50MB upload limit.")
            out.write(chunk)

    if size == 0:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    return stored_path, file_type, file.filename


def extract_metadata(path: Path, file_type: str, sheet_name: str | None = None) -> tuple[int, int, list[str]]:
    df = read_dataframe(path, file_type, sheet_name)
    if df.shape[1] == 0:
        raise HTTPException(status_code=400, detail="Dataset has no columns.")
    columns = [str(c) for c in df.columns]
    return df.shape[0], df.shape[1], columns


def get_preview(
    path: Path, file_type: str, offset: int, limit: int, sheet_name: str | None = None
) -> tuple[list[dict], int]:
    df = read_dataframe(path, file_type, sheet_name)
    total = len(df)
    sliced = df.iloc[offset : offset + limit]
    # Route through pandas' own JSON encoder so NaN/NaT/numpy scalars become
    # valid JSON null/native types instead of failing standard json.dumps.
    records = json.loads(sliced.to_json(orient="records", date_format="iso"))
    return records, total
