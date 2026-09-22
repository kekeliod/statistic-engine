from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chart import ChartOut


class RoleOut(BaseModel):
    name: str
    arity: str
    dtypes: list[str]
    description: str


class MethodSpecOut(BaseModel):
    key: str
    label: str
    category: str
    description: str
    when_to_use: str
    roles: list[RoleOut]
    param_defaults: dict[str, Any]
    bayesian_supported: bool


class RecommendationOut(BaseModel):
    objective_index: int | None
    objective_text: str
    method_key: str
    method_label: str
    rationale: str
    confidence: str
    suggested_variables: dict[str, Any]
    chart_suggestion: str
    alternative_method_key: str | None = None
    source: str


class AnalysisCreate(BaseModel):
    dataset_id: int
    method: str
    variables: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    objective_index: int | None = None


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    dataset_id: int
    objective_index: int | None
    method: str
    variables: dict[str, Any]
    params: dict[str, Any]
    status: str
    result: dict[str, Any] | None
    error: str | None
    interpretation: str | None
    charts: list[ChartOut] = []
    created_at: datetime
    updated_at: datetime
