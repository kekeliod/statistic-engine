"""Helpers shared by method runners."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.stats.base import AnalysisError, clean


def numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
    s = pd.to_numeric(df[col], errors="coerce")
    if s.notna().sum() == 0:
        raise AnalysisError(f"Column '{col}' has no usable numeric values.")
    return s


def group_levels(df: pd.DataFrame, col: str, *, min_groups: int = 2, max_groups: int | None = None) -> list:
    levels = [lvl for lvl in pd.unique(df[col].dropna())]
    levels_sorted = sorted(levels, key=lambda v: str(v))
    if len(levels_sorted) < min_groups:
        raise AnalysisError(
            f"Grouping column '{col}' has {len(levels_sorted)} distinct value(s); "
            f"this test needs at least {min_groups}."
        )
    if max_groups is not None and len(levels_sorted) > max_groups:
        raise AnalysisError(
            f"Grouping column '{col}' has {len(levels_sorted)} distinct values; "
            f"this test handles at most {max_groups}. Use a method for multiple groups."
        )
    return levels_sorted


def describe_groups(df: pd.DataFrame, outcome: str, group: str) -> dict:
    """Per-group n / mean / sd / median for plotting and reporting."""
    out: dict[str, dict] = {}
    for lvl, sub in df.groupby(group):
        vals = pd.to_numeric(sub[outcome], errors="coerce").dropna()
        out[str(lvl)] = {
            "n": int(len(vals)),
            "mean": clean(vals.mean()),
            "sd": clean(vals.std(ddof=1)) if len(vals) > 1 else 0.0,
            "median": clean(vals.median()),
            "min": clean(vals.min()),
            "max": clean(vals.max()),
        }
    return out


def group_summary_table(groups: dict, outcome_label: str) -> dict:
    return {
        "title": f"{outcome_label} by group",
        "columns": ["Group", "n", "Mean", "SD", "Median"],
        "rows": [
            [name, g["n"], _fmt(g["mean"]), _fmt(g["sd"]), _fmt(g["median"])]
            for name, g in groups.items()
        ],
    }


def _fmt(v) -> str:
    if v is None:
        return "—"
    return f"{v:.4g}"


def parse_bf10(raw) -> float | None:
    """pingouin returns BF10 as a string like '223.099' or '4.1e+04'."""
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def ci_pair(raw) -> tuple[float | None, float | None]:
    if raw is None:
        return None, None
    arr = np.asarray(raw, dtype=float).ravel()
    if arr.size < 2:
        return None, None
    return float(arr[0]), float(arr[1])
