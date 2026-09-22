"""Shared result structures for the statistics engine.

`StatResult` is a plain dict (JSON-serialisable, stored on Analysis.result). The
builders here keep the shape consistent across every method and normalise
NaN/inf to None so the payload is valid JSON.
"""
from __future__ import annotations

import math
from typing import Any


def clean(value: Any) -> Any:
    """NaN / inf / numpy scalars -> JSON-safe Python values."""
    if value is None:
        return None
    if isinstance(value, (bool, str, int)):
        return value
    try:
        f = float(value)
    except (TypeError, ValueError):
        return value
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def effect_magnitude(kind: str, value: float | None) -> str | None:
    """Verbal magnitude label for a standardised effect size."""
    if value is None:
        return None
    v = abs(value)
    thresholds = {
        "d": [(0.2, "negligible"), (0.5, "small"), (0.8, "medium")],  # Cohen's d
        "r": [(0.1, "negligible"), (0.3, "small"), (0.5, "medium")],  # correlation r
        "eta2": [(0.01, "negligible"), (0.06, "small"), (0.14, "medium")],  # eta-squared
        "cramer": [(0.1, "negligible"), (0.3, "small"), (0.5, "medium")],
    }
    scale = thresholds.get(kind)
    if scale is None:
        return None
    for cutoff, label in scale:
        if v < cutoff:
            return label
    return "large"


def bayes_factor_strength(bf10: float | None) -> str | None:
    """Jeffreys' verbal scale for BF10 (evidence for H1 over H0)."""
    if bf10 is None:
        return None
    bf = float(bf10)
    inv = 1.0 / bf if bf > 0 else float("inf")
    if bf >= 100:
        return "extreme evidence for an effect"
    if bf >= 30:
        return "very strong evidence for an effect"
    if bf >= 10:
        return "strong evidence for an effect"
    if bf >= 3:
        return "moderate evidence for an effect"
    if bf > 1:
        return "anecdotal evidence for an effect"
    if bf == 1:
        return "no evidence either way"
    if inv < 3:
        return "anecdotal evidence for no effect"
    if inv < 10:
        return "moderate evidence for no effect"
    if inv < 30:
        return "strong evidence for no effect"
    return "very strong evidence for no effect"


def frequentist_block(
    *,
    statistic_name: str,
    statistic_value: float | None,
    p_value: float | None,
    df: float | None = None,
    estimate: dict | None = None,
    effect_size: dict | None = None,
    summary: str = "",
    extra: dict | None = None,
) -> dict:
    block = {
        "statistic": {"name": statistic_name, "value": clean(statistic_value)},
        "df": clean(df),
        "p_value": clean(p_value),
        "estimate": estimate,
        "effect_size": effect_size,
        "summary": summary,
    }
    if extra:
        block.update(extra)
    return block


def bayesian_block(
    *,
    available: bool,
    bayes_factor_10: float | None = None,
    prior: str | None = None,
    summary: str = "",
    note: str | None = None,
) -> dict:
    interpretation = bayes_factor_strength(bayes_factor_10) if available else None
    return {
        "available": available,
        "bayes_factor_10": clean(bayes_factor_10),
        "interpretation": interpretation,
        "prior": prior,
        "summary": summary,
        "note": note,
    }


# Standard note for methods pingouin has no Bayes factor for.
NO_BF_NOTE = (
    "pingouin does not provide a Bayes factor for this test, so only the "
    "frequentist result is shown. A full Bayesian version (posterior "
    "distributions / credible intervals via PyMC) is a planned upgrade."
)


def estimate_block(
    name: str,
    value: float | None,
    ci_low: float | None = None,
    ci_high: float | None = None,
    ci_level: float = 0.95,
) -> dict:
    return {
        "name": name,
        "value": clean(value),
        "ci_low": clean(ci_low),
        "ci_high": clean(ci_high),
        "ci_level": ci_level,
    }


def effect_size_block(name: str, kind: str, value: float | None) -> dict:
    return {
        "name": name,
        "value": clean(value),
        "magnitude": effect_magnitude(kind, value),
    }


def stat_result(
    *,
    method: str,
    method_label: str,
    n_used: int,
    n_excluded: int,
    frequentist: dict,
    bayesian: dict,
    assumptions: list[dict] | None = None,
    tables: list[dict] | None = None,
    groups: dict | None = None,
) -> dict:
    return {
        "method": method,
        "method_label": method_label,
        "n_used": n_used,
        "n_excluded": n_excluded,
        "frequentist": frequentist,
        "bayesian": bayesian,
        "assumptions": assumptions or [],
        "tables": tables or [],
        "groups": groups or {},
    }


class AnalysisError(ValueError):
    """Raised by method runners / execution for a user-fixable problem
    (wrong column type, too few groups, all values missing, ...)."""
