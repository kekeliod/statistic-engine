"""Reusable assumption checks.

Each returns a dict:
    {key, label, passed, detail, p_value, recommendation}

`passed` is a best-effort call; `recommendation` names the alternative to fall
back to when it fails. Checks never raise on degenerate input — they return
`passed=None` with an explanatory detail instead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps


def _check(key, label, passed, detail, p_value=None, recommendation=None):
    return {
        "key": key,
        "label": label,
        "passed": passed,
        "detail": detail,
        "p_value": None if p_value is None else float(p_value),
        "recommendation": recommendation,
    }


def check_normality(values, group_label: str = "", alpha: float = 0.05, alternative: str = "") -> dict:
    x = pd.Series(values).dropna().astype(float)
    label = f"Normality of {group_label}".strip() + " (Shapiro–Wilk)"
    if len(x) < 3:
        return _check("normality", label, None, "Too few values to test normality (need at least 3).")
    if len(x) > 5000:
        x = x.sample(5000, random_state=0)
    try:
        stat, p = sps.shapiro(x)
    except Exception as exc:  # noqa: BLE001
        return _check("normality", label, None, f"Shapiro–Wilk could not run: {exc}")
    skew = float(sps.skew(x))
    passed = bool(p >= alpha)
    detail = (
        f"W = {stat:.3f}, p = {p:.4f}; skew = {skew:.2f}. "
        + ("Distribution is consistent with normal." if passed
           else "Distribution departs from normal.")
    )
    rec = alternative or "a non-parametric alternative"
    return _check("normality", label, passed, detail, p, None if passed else f"Consider {rec}.")


def check_homogeneity(*groups, alpha: float = 0.05, alternative: str = "") -> dict:
    cleaned = [pd.Series(g).dropna().astype(float) for g in groups]
    cleaned = [g for g in cleaned if len(g) >= 2]
    label = "Equal variances across groups (Levene)"
    if len(cleaned) < 2:
        return _check("homogeneity", label, None, "Not enough groups with data to test equality of variance.")
    try:
        stat, p = sps.levene(*cleaned, center="median")
    except Exception as exc:  # noqa: BLE001
        return _check("homogeneity", label, None, f"Levene's test could not run: {exc}")
    passed = bool(p >= alpha)
    detail = (
        f"Levene W = {stat:.3f}, p = {p:.4f}. "
        + ("Group variances are similar." if passed else "Group variances differ.")
    )
    rec = alternative or "Welch's correction or a non-parametric test"
    return _check("homogeneity", label, passed, detail, p, None if passed else f"Consider {rec}.")


def check_sample_size(n: int, minimum: int, what: str = "each group") -> dict:
    passed = n >= minimum
    return _check(
        "sample_size",
        "Adequate sample size",
        passed,
        f"n = {n} ({what}); rule-of-thumb minimum is {minimum}.",
        recommendation=None if passed else "Interpret with caution and collect more data if possible.",
    )


def check_expected_counts(expected: np.ndarray) -> dict:
    label = "Expected cell counts ≥ 5 (chi-square validity)"
    exp = np.asarray(expected, dtype=float)
    n_small = int((exp < 5).sum())
    frac_small = n_small / exp.size if exp.size else 1.0
    passed = frac_small == 0
    detail = (
        f"{n_small} of {exp.size} cells have an expected count below 5 "
        f"(minimum expected = {exp.min():.2f})."
    )
    return _check(
        "expected_counts", label, passed, detail,
        recommendation=None if passed else "Consider Fisher's exact test or combining sparse categories.",
    )


def check_multicollinearity(design: pd.DataFrame) -> dict:
    """Variance Inflation Factor across predictor columns (no intercept column)."""
    label = "Low multicollinearity among predictors (VIF < 5)"
    X = design.dropna().astype(float)
    if X.shape[1] < 2 or len(X) <= X.shape[1] + 1:
        return _check("multicollinearity", label, None, "Too few predictors or rows to assess VIF.")
    try:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        Xc = X.assign(_const=1.0)
        vifs = {
            col: float(variance_inflation_factor(Xc.values, i))
            for i, col in enumerate(Xc.columns)
            if col != "_const"
        }
    except Exception as exc:  # noqa: BLE001
        return _check("multicollinearity", label, None, f"VIF could not be computed: {exc}")
    worst = max(vifs, key=vifs.get)
    passed = vifs[worst] < 5
    detail = "VIF: " + ", ".join(f"{k} = {v:.1f}" for k, v in vifs.items())
    return _check(
        "multicollinearity", label, passed, detail,
        recommendation=None if passed else f"'{worst}' is collinear with other predictors; consider dropping it.",
    )


def check_homoscedasticity(resid, fitted, alpha: float = 0.05) -> dict:
    """Breusch–Pagan test for constant error variance in a regression."""
    label = "Constant residual variance (Breusch–Pagan)"
    try:
        from statsmodels.stats.diagnostic import het_breuschpagan
        import statsmodels.api as sm
        lm, lm_p, f, f_p = het_breuschpagan(np.asarray(resid), sm.add_constant(np.asarray(fitted)))
    except Exception as exc:  # noqa: BLE001
        return _check("homoscedasticity", label, None, f"Breusch–Pagan could not run: {exc}")
    passed = bool(lm_p >= alpha)
    detail = (
        f"LM p = {lm_p:.4f}. "
        + ("Residual spread looks constant." if passed else "Residual spread changes with the fitted value.")
    )
    return _check(
        "homoscedasticity", label, passed, detail, lm_p,
        recommendation=None if passed else "Consider robust (HC3) standard errors or transforming the outcome.",
    )


def check_residual_normality(resid, alpha: float = 0.05) -> dict:
    out = check_normality(resid, group_label="regression residuals", alpha=alpha,
                          alternative="robust standard errors or a transformed outcome")
    return out


def check_independence(detail: str = "") -> dict:
    """Cannot be tested from the data alone — surfaced as an advisory."""
    return _check(
        "independence",
        "Independent observations",
        None,
        detail or "The test assumes observations are independent (no repeated measures on the "
        "same unit, no clustering). This cannot be verified from the data alone — confirm it "
        "matches how the data were collected.",
        recommendation="If observations are paired or clustered, use a paired/mixed-effects method instead.",
    )
