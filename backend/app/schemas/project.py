from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    research_aim: str = Field(min_length=1)
    objectives: list[str] = Field(default_factory=list)
    research_questions: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    title: str | None = None
    research_aim: str | None = None
    objectives: list[str] | None = None
    research_questions: list[str] | None = None
    hypotheses: list[str] | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    research_aim: str
    objectives: list[str]
    research_questions: list[str]
    hypotheses: list[str]
    created_at: datetime
    updated_at: datetime


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    research_aim: str
    created_at: datetime
    updated_at: datetime
    dataset_count: int = 0
