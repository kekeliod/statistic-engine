"""Correlation: Pearson (with Bayes factor) and Spearman."""
from __future__ import annotations

import pandas as pd
import pingouin as pg

from app.services.stats import assumptions as A
from app.services.stats.base import (
    NO_BF_NOTE,
    AnalysisError,
    bayesian_block,
    effect_size_block,
    estimate_block,
    frequentist_block,
    stat_result,
)
from app.services.stats.methods._shared import ci_pair, numeric_series, parse_bf10


def _corr(df: pd.DataFrame, variables: dict, params: dict, method: str) -> dict:
    x_col, y_col = variables["variable_1"], variables["variable_2"]
    alpha = float(params.get("alpha", 0.05))

    work = df[[x_col, y_col]].copy()
    work[x_col] = numeric_series(work, x_col)
    work[y_col] = numeric_series(work, y_col)
    work = work.dropna()
    if len(work) < 4:
        raise AnalysisError("Need at least 4 complete pairs to estimate a correlation.")

    res = pg.corr(work[x_col], work[y_col], method=method).iloc[0]
    r = float(res["r"])
    p = float(res["p_val"])
    lo, hi = ci_pair(res["CI95"])
    bf10 = parse_bf10(res["BF10"]) if "BF10" in res.index else None
    sig = p < alpha
    direction = "positive" if r > 0 else "negative"
    verdict = "a statistically significant" if sig else "no statistically significant"
    label = "Pearson correlation" if method == "pearson" else "Spearman rank correlation"
    stat_name = "r" if method == "pearson" else "rho"

    freq = frequentist_block(
        statistic_name=stat_name,
        statistic_value=r,
        p_value=p,
        df=len(work) - 2,
        estimate=estimate_block(f"{stat_name} ({x_col}, {y_col})", r, lo, hi),
        effect_size=effect_size_block(f"{label} coefficient", "r", r),
        summary=(
            f"{label} found {verdict} {direction} relationship between {x_col} and {y_col}; "
            f"{stat_name} = {r:.3f}"
            + (f" (95% CI {lo:.2f} to {hi:.2f})" if lo is not None else "")
            + f", p = {p:.4f}, n = {len(work)}."
        ),
    )
    if method == "pearson":
        bayes = bayesian_block(
            available=bf10 is not None,
            bayes_factor_10=bf10,
            prior="stretched Beta(1/3, 1/3) on r (pingouin default)",
            summary=(f"BF10 = {bf10:.3g}." if bf10 is not None else ""),
            note=None if bf10 is not None else NO_BF_NOTE,
        )
    else:
        bayes = bayesian_block(available=False, summary="", note=NO_BF_NOTE)

    checks = []
    if method == "pearson":
        checks += [
            A.check_normality(work[x_col], x_col, alpha, "the Spearman rank correlation"),
            A.check_normality(work[y_col], y_col, alpha, "the Spearman rank correlation"),
        ]
    checks.append(A.check_independence())

    return stat_result(
        method=method,
        method_label=label,
        n_used=len(work),
        n_excluded=0,
        frequentist=freq,
        bayesian=bayes,
        assumptions=checks,
        tables=[{
            "title": "Correlation summary",
            "columns": ["Pair", stat_name, "95% CI", "p", "n"],
            "rows": [[f"{x_col} × {y_col}", f"{r:.3f}",
                      f"[{lo:.2f}, {hi:.2f}]" if lo is not None else "—",
                      f"{p:.4f}", len(work)]],
        }],
        groups={"x": x_col, "y": y_col, "method": method},
    )


def pearson(df: pd.DataFrame, variables: dict, params: dict) -> dict:
    return _corr(df, variables, params, "pearson")


def spearman(df: pd.DataFrame, variables: dict, params: dict) -> dict:
    return _corr(df, variables, params, "spearman")
