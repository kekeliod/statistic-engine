"""Descriptive statistics — summarises variables, no inferential test."""
from __future__ import annotations

import pandas as pd

from app.services.stats.base import AnalysisError, bayesian_block, clean, frequentist_block, stat_result


def describe(df: pd.DataFrame, variables: dict, params: dict) -> dict:
    cols = variables["variables"]
    if isinstance(cols, str):
        cols = [cols]
    if not cols:
        raise AnalysisError("Select at least one variable to describe.")

    numeric_rows, cat_tables, group_stats = [], [], {}
    for col in cols:
        s = df[col].dropna()
        coerced = pd.to_numeric(s, errors="coerce")
        if len(s) and coerced.notna().mean() >= 0.7:
            v = coerced.dropna()
            q1, q3 = v.quantile(0.25), v.quantile(0.75)
            stats = {
                "n": int(v.count()), "missing": int(df[col].isna().sum()),
                "mean": clean(v.mean()), "sd": clean(v.std(ddof=1)) if len(v) > 1 else 0.0,
                "median": clean(v.median()), "iqr": clean(q3 - q1),
                "min": clean(v.min()), "max": clean(v.max()),
            }
            group_stats[col] = stats
            numeric_rows.append([col, stats["n"], f"{stats['mean']:.4g}", f"{stats['sd']:.4g}",
                                 f"{stats['median']:.4g}", f"{stats['iqr']:.4g}",
                                 f"{stats['min']:.4g}", f"{stats['max']:.4g}"])
        else:
            counts = s.astype(str).value_counts()
            total = int(counts.sum())
            cat_tables.append({
                "title": f"Frequencies: {col}",
                "columns": [col, "Count", "Percent"],
                "rows": [[str(k), int(c), f"{100 * c / total:.1f}%"] for k, c in counts.items()],
            })
            group_stats[col] = {"n": total, "categories": {str(k): int(c) for k, c in counts.items()}}

    tables = []
    if numeric_rows:
        tables.append({
            "title": "Descriptive statistics (numeric)",
            "columns": ["Variable", "n", "Mean", "SD", "Median", "IQR", "Min", "Max"],
            "rows": numeric_rows,
        })
    tables.extend(cat_tables)

    freq = frequentist_block(
        statistic_name="—", statistic_value=None, p_value=None,
        summary=f"Summary of {len(cols)} variable(s): "
                + ", ".join(cols) + ". No hypothesis test is performed for descriptive statistics.",
    )
    bayes = bayesian_block(
        available=False, summary="",
        note="Descriptive statistics summarise the sample; there is no hypothesis being tested, "
             "so neither a p-value nor a Bayes factor applies.",
    )
    return stat_result(
        method="descriptive",
        method_label="Descriptive statistics",
        n_used=len(df),
        n_excluded=0,
        frequentist=freq,
        bayesian=bayes,
        assumptions=[],
        tables=tables,
        groups={"variables": cols, "stats": group_stats},
    )
