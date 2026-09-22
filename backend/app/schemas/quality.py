from pydantic import BaseModel


class TopValue(BaseModel):
    value: str
    count: int


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    non_null_count: int
    missing_count: int
    missing_pct: float
    unique_count: int
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None
    top_values: list[TopValue] | None = None


class DuplicatesReport(BaseModel):
    duplicate_row_count: int
    duplicate_row_pct: float
    example_groups: list[list[int]]


class OutlierColumnReport(BaseModel):
    column: str
    method: str
    count: int
    pct: float
    lower_bound: float | None
    upper_bound: float | None
    example_row_indices: list[int]
    example_values: list[float | None]


class InvalidValueColumnReport(BaseModel):
    column: str
    reason: str
    detail: str
    count: int
    examples: list[str]


class QualityScoreBreakdown(BaseModel):
    overall: int
    completeness: int
    validity: int
    consistency: int
    duplicates: int
    outliers: int
    notes: list[str]
    formula: str


class DataQualityReport(BaseModel):
    n_rows: int
    n_columns: int
    columns: list[ColumnProfile]
    duplicates: DuplicatesReport
    outliers: list[OutlierColumnReport]
    invalid_values: list[InvalidValueColumnReport]
    score: QualityScoreBreakdown
