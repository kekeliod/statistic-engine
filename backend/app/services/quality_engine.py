"""Deterministic dataset profiling and data-quality assessment.

Everything here is plain pandas/NumPy computation — no LLM involved. This is the
"ground truth" the AI layer (Phase 3+) will later reason over and explain in plain
language; it never computes the numbers itself.

Nothing here deletes or modifies data. Duplicates, invalid values, and outliers are
flagged with concrete examples for the researcher to review, per the project's
guardrail against silently changing the dataset.
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from app.services.type_inference import (
    ColumnTypeInfo,
    coerced_numeric_series,
    infer_all_types,
    try_parse_numeric_token,
)

MAX_EXAMPLES = 10
TOP_CATEGORY_LIMIT = 5

# Deliberately small and transparent: only fires for column-name patterns with
# widely-agreed, unambiguous physical bounds. A flagged value is a strong "this
# looks wrong" signal, not a guess at domain rules we don't actually know.
KNOWN_RANGES: list[tuple[re.Pattern, float, float, str]] = [
    (re.compile(r"\bage\b", re.IGNORECASE), 0, 120, "age in years"),
    (re.compile(r"percent|_pct\b|%", re.IGNORECASE), 0, 100, "percentage"),
    (re.compile(r"\bph\b|ph[-_]|ph$", re.IGNORECASE), 0, 14, "pH"),
    (re.compile(r"latitude", re.IGNORECASE), -90, 90, "latitude"),
    (re.compile(r"longitude", re.IGNORECASE), -180, 180, "longitude"),
]


def _clean(value: float) -> float | None:
    """NaN/inf are not valid JSON — normalize to None."""
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return None
    return float(value)


def profile_dataset(df: pd.DataFrame, types: dict[str, ColumnTypeInfo]) -> dict[str, Any]:
    n_rows = len(df)
    columns = []
    for name in df.columns:
        name = str(name)
        series = df[name]
        non_null = series.dropna()
        missing_count = int(series.isna().sum())
        info = types[name]

        col: dict[str, Any] = {
            "name": name,
            "dtype": info.dtype,
            "non_null_count": int(len(non_null)),
            "missing_count": missing_count,
            "missing_pct": round(missing_count / n_rows * 100, 2) if n_rows else 0.0,
            "unique_count": int(non_null.nunique()),
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
            "top_values": None,
        }

        if info.is_numeric_like and len(non_null) > 0:
            numeric = (
                non_null if pd.api.types.is_numeric_dtype(series) else coerced_numeric_series(non_null)
            )
            numeric = numeric.dropna()
            if len(numeric) > 0:
                col["mean"] = _clean(numeric.mean())
                col["median"] = _clean(numeric.median())
                col["std"] = _clean(numeric.std()) if len(numeric) > 1 else 0.0
                col["min"] = _clean(numeric.min())
                col["max"] = _clean(numeric.max())
        elif info.dtype in ("categorical", "binary") and len(non_null) > 0:
            counts = non_null.value_counts().head(TOP_CATEGORY_LIMIT)
            col["top_values"] = [{"value": str(v), "count": int(c)} for v, c in counts.items()]

        columns.append(col)

    return {"n_rows": n_rows, "n_columns": len(df.columns), "columns": columns}


def detect_duplicates(df: pd.DataFrame) -> dict[str, Any]:
    n_rows = len(df)
    dup_mask = df.duplicated(keep=False)
    duplicate_row_count = int(df.duplicated(keep="first").sum())

    example_groups: list[list[int]] = []
    if dup_mask.any():
        dup_rows = df[dup_mask]
        # Group by the full row content to show which specific rows repeat together.
        grouped = dup_rows.astype(str).groupby(list(dup_rows.columns)).apply(
            lambda g: list(g.index), include_groups=False
        )
        for indices in grouped:
            if len(indices) > 1:
                example_groups.append([int(i) for i in indices])
            if len(example_groups) >= MAX_EXAMPLES:
                break

    return {
        "duplicate_row_count": duplicate_row_count,
        "duplicate_row_pct": round(duplicate_row_count / n_rows * 100, 2) if n_rows else 0.0,
        "example_groups": example_groups,
    }


def detect_outliers(df: pd.DataFrame, types: dict[str, ColumnTypeInfo]) -> list[dict[str, Any]]:
    """IQR method (Tukey's fences): flags values outside [Q1-1.5*IQR, Q3+1.5*IQR].
    Chosen over Z-score because it doesn't assume normality and isn't itself
    distorted by the extreme values it's trying to detect.
    """
    results = []
    for name, info in types.items():
        if not info.is_numeric_like or info.dtype == "binary":
            continue
        series = df[name].dropna()
        numeric = (
            series if pd.api.types.is_numeric_dtype(df[name]) else coerced_numeric_series(series)
        ).dropna()
        if len(numeric) < 4:
            continue

        q1, q3 = np.percentile(numeric, [25, 75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (numeric < lower) | (numeric > upper)
        count = int(mask.sum())
        if count == 0:
            continue

        outlier_values = numeric[mask]
        results.append(
            {
                "column": name,
                "method": "IQR (1.5x Tukey fence)",
                "count": count,
                "pct": round(count / len(numeric) * 100, 2),
                "lower_bound": _clean(lower),
                "upper_bound": _clean(upper),
                "example_row_indices": [int(i) for i in outlier_values.index[:MAX_EXAMPLES]],
                "example_values": [_clean(v) for v in outlier_values.head(MAX_EXAMPLES)],
            }
        )
    return results


def detect_invalid_values(df: pd.DataFrame, types: dict[str, ColumnTypeInfo]) -> list[dict[str, Any]]:
    results = []
    for name, info in types.items():
        series = df[name]
        non_null = series.dropna()

        # Numeric-like text columns: minority of values that didn't parse as numbers
        # at all (distinct from lab-style "<0.005", which IS treated as numeric).
        # Re-parses exactly rather than counting against the capped sample list,
        # so this stays accurate when there are more than MAX_EXAMPLES distinct
        # non-numeric values.
        if info.dtype == "numeric" and info.non_numeric_tokens:
            count = int(non_null.map(try_parse_numeric_token).isna().sum())
            if count > 0:
                results.append(
                    {
                        "column": name,
                        "reason": "non_numeric_tokens",
                        "detail": "Column is mostly numeric but contains values that don't parse as numbers.",
                        "count": count,
                        "examples": info.non_numeric_tokens[:MAX_EXAMPLES],
                    }
                )

        # Known-range violations for well-understood field name patterns.
        if info.is_numeric_like:
            for pattern, lo, hi, label in KNOWN_RANGES:
                if pattern.search(name):
                    numeric = (
                        non_null
                        if pd.api.types.is_numeric_dtype(series)
                        else coerced_numeric_series(non_null)
                    ).dropna()
                    out_of_range = numeric[(numeric < lo) | (numeric > hi)]
                    if len(out_of_range) > 0:
                        results.append(
                            {
                                "column": name,
                                "reason": "out_of_known_range",
                                "detail": f"Values outside the plausible range for {label} ({lo}–{hi}).",
                                "count": int(len(out_of_range)),
                                "examples": [str(_clean(v)) for v in out_of_range.head(MAX_EXAMPLES)],
                            }
                        )
                    break  # first matching pattern only
    return results


def _consistency_score(df: pd.DataFrame, categorical_cols: list[str]) -> tuple[float, list[str]]:
    if not categorical_cols:
        return 100.0, ["No categorical columns detected — consistency check not applicable, scored 100 by default."]

    inconsistent_cols = 0
    for name in categorical_cols:
        raw_values = df[name].dropna().astype(str)
        normalized = raw_values.str.strip().str.lower()
        if raw_values.nunique() > normalized.nunique():
            inconsistent_cols += 1

    score = 100 * (1 - inconsistent_cols / len(categorical_cols))
    return score, []


def run_quality_report(df: pd.DataFrame) -> dict[str, Any]:
    types = infer_all_types(df)
    profile = profile_dataset(df, types)
    duplicates = detect_duplicates(df)
    outliers = detect_outliers(df, types)
    invalid_values = detect_invalid_values(df, types)

    n_rows, n_columns = len(df), len(df.columns)
    total_cells = n_rows * n_columns
    total_missing = sum(c["missing_count"] for c in profile["columns"])
    completeness = 100.0 if total_cells == 0 else 100 * (1 - total_missing / total_cells)

    duplicates_score = 100 * (1 - duplicates["duplicate_row_count"] / n_rows) if n_rows else 100.0

    numeric_cols = [name for name, info in types.items() if info.is_numeric_like and info.dtype != "binary"]
    notes: list[str] = []
    if numeric_cols:
        outlier_pct_by_col = {o["column"]: o["pct"] for o in outliers}
        avg_outlier_pct = sum(outlier_pct_by_col.get(c, 0.0) for c in numeric_cols) / len(numeric_cols)
        outliers_score = 100 - avg_outlier_pct
    else:
        outliers_score = 100.0
        notes.append("No numeric columns detected — outlier check not applicable, scored 100 by default.")

    checkable_cells = sum(
        c["non_null_count"]
        for c in profile["columns"]
        if types[c["name"]].dtype == "numeric" or any(p.search(c["name"]) for p, *_ in KNOWN_RANGES)
    )
    invalid_count = sum(v["count"] for v in invalid_values)
    if checkable_cells > 0:
        validity = 100 * (1 - min(invalid_count, checkable_cells) / checkable_cells)
    else:
        validity = 100.0
        notes.append("No columns matched an invalid-value check — validity scored 100 by default.")

    categorical_cols = [name for name, info in types.items() if info.dtype == "categorical"]
    consistency, consistency_notes = _consistency_score(df, categorical_cols)
    notes.extend(consistency_notes)

    sub_scores = {
        "completeness": completeness,
        "validity": validity,
        "consistency": consistency,
        "duplicates": duplicates_score,
        "outliers": outliers_score,
    }
    overall = sum(sub_scores.values()) / len(sub_scores)

    score = {
        "overall": round(max(0, min(100, overall))),
        "completeness": round(max(0, min(100, completeness))),
        "validity": round(max(0, min(100, validity))),
        "consistency": round(max(0, min(100, consistency))),
        "duplicates": round(max(0, min(100, duplicates_score))),
        "outliers": round(max(0, min(100, outliers_score))),
        "notes": notes,
        "formula": "overall = mean(completeness, validity, consistency, duplicates, outliers), each 0-100",
    }

    return {
        "n_rows": profile["n_rows"],
        "n_columns": profile["n_columns"],
        "columns": profile["columns"],
        "duplicates": duplicates,
        "outliers": outliers,
        "invalid_values": invalid_values,
        "score": score,
    }
