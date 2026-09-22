from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    format: str = Field(default="html", pattern="^(html|docx)$")
    analysis_ids: list[int] | None = None
    title: str | None = None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    format: str
    created_at: datetime
