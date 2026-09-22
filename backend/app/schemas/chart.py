from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    analysis_id: int | None
    kind: str
    title: str
    spec: dict
    created_at: datetime


class ChartCreate(BaseModel):
    kind: str | None = None
