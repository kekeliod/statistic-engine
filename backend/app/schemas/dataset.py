from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    original_filename: str
    file_type: str
    sheet_name: str | None
    n_rows: int
    n_columns: int
    columns: list[str]
    version: int
    is_active: bool
    uploaded_at: datetime


class DatasetPreview(BaseModel):
    columns: list[str]
    rows: list[dict]
    total_rows: int
    offset: int
    limit: int


class SheetSelectionRequired(BaseModel):
    requires_sheet_selection: bool = True
    sheets: list[str]
