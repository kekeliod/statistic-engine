"""Deterministic column-type classification.

Used by the profiling and data-quality engines so they agree on what counts as
"numeric" — including lab-style censored values like "<0.005", which are common
in scientific measurement data and should not be treated as broken text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Column is treated as an identifier if its name looks like one AND its values are
# almost all unique — name alone isn't enough (e.g. a "code" column of repeated
# category codes is categorical, not an identifier).
ID_NAME_RE = re.compile(r"(^id$|_id$|^id_|code|stn\.?code|station|serial|uuid)", re.IGNORECASE)

# A text column is treated as numeric if at least this fraction of its non-null
# values parse as numbers (after stripping lab-style "<"/">" censoring prefixes).
NUMERIC_LIKE_THRESHOLD = 0.7


@dataclass
class ColumnTypeInfo:
    name: str
    dtype: str  # "numeric" | "binary" | "categorical" | "datetime" | "identifier" | "text"
    is_numeric_like: bool
    non_numeric_tokens: list[str] = field(default_factory=list)


def try_parse_numeric_token(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    # Lab-style censoring: "<0.005" (below detection limit), ">100" (above range).
    # Parsed at the reported boundary value — a documented simplification, not a
    # claim about the true underlying value.
    stripped = text.lstrip("<>").strip()
    try:
        return float(stripped)
    except ValueError:
        return None


def classify_column(series: pd.Series, name: str) -> ColumnTypeInfo:
    non_null = series.dropna()
    n = len(non_null)

    if n == 0:
        return ColumnTypeInfo(name=name, dtype="text", is_numeric_like=False)

    nunique = non_null.nunique()

    if pd.api.types.is_datetime64_any_dtype(series):
        return ColumnTypeInfo(name=name, dtype="datetime", is_numeric_like=False)

    if pd.api.types.is_numeric_dtype(series):
        dtype = "binary" if nunique <= 2 else "numeric"
        return ColumnTypeInfo(name=name, dtype=dtype, is_numeric_like=True)

    # Object/text column: how much of it parses as numeric?
    # Series.map() silently turns a returned None into NaN once the result Series
    # is float-typed, so check with pd.isna() here rather than `is None`.
    parsed = non_null.map(try_parse_numeric_token)
    numeric_fraction = float(parsed.notna().mean())
    non_numeric_tokens = sorted({str(v) for v, p in zip(non_null, parsed) if pd.isna(p)})[:10]

    if numeric_fraction >= NUMERIC_LIKE_THRESHOLD:
        return ColumnTypeInfo(
            name=name, dtype="numeric", is_numeric_like=True, non_numeric_tokens=non_numeric_tokens
        )

    if ID_NAME_RE.search(name) and nunique / n > 0.9:
        return ColumnTypeInfo(name=name, dtype="identifier", is_numeric_like=False)

    if nunique <= 2:
        return ColumnTypeInfo(name=name, dtype="binary", is_numeric_like=False)

    if nunique <= max(20, int(n * 0.5)):
        return ColumnTypeInfo(name=name, dtype="categorical", is_numeric_like=False)

    return ColumnTypeInfo(name=name, dtype="text", is_numeric_like=False)


def infer_all_types(df: pd.DataFrame) -> dict[str, ColumnTypeInfo]:
    return {str(col): classify_column(df[col], str(col)) for col in df.columns}


def coerced_numeric_series(series: pd.Series) -> pd.Series:
    """Best-effort numeric coercion tolerant of lab-style censoring tokens."""
    return series.map(try_parse_numeric_token).astype(float)
