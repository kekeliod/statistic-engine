"""Linear and logistic regression (statsmodels)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from app.services.stats import assumptions as A
from app.services.stats.base import (
    NO_BF_NOTE,
    AnalysisError,
    bayesian_block,
    clean,
    effect_size_block,
    estimate_block,
    frequentist_block,
    stat_result,
)
from app.services.stats.methods._shared import numeric_series


def _design(df: pd.DataFrame, outcome: str, predictors: list[str]):
    work = df[[outcome, *predictors]].copy()
    work[outcome] = pd.to_numeric(work[outcome], errors="coerce")
    num_predictors, cat_predictors = [], []
    for p in predictors:
        coerced = pd.to_numeric(work[p], errors="coerce")
        if coerced.notna().mean() >= 0.7:
            work[p] = coerced
            num_predictors.append(p)
        else:
            cat_predictors.append(p)
    work = work.dropna()
    if len(work) <= len(predictors) + 2:
        raise AnalysisError("Not enough complete rows to fit this regression.")
    X = pd.get_dummies(work[predictors], columns=cat_predictors, drop_first=True, dtype=float)
    X = sm.add_constant(X, has_constant="add")
    return work, X.astype(float), work[outcome], num_predictors, cat_predictors


def linear_regression(df: pd.DataFrame, variables: dict, params: dict) -> dict:
    outcome = variables["outcome"]
    predictors = variables["predictors"]
    if isinstance(predictors, str):
        predictors = [predictors]
    if not predictors:
        raise AnalysisError("Select at least one predictor.")
    alpha = float(params.get("alpha", 0.05))

    work, X, y, num_predictors, _ = _design(df, outcome, predictors)
    model = sm.OLS(y, X).fit()

    coef_rows = []
    for name in X.columns:
        ci = model.conf_int(alpha=alpha).loc[name]
        coef_rows.append([
            "intercept" if name == "const" else name,
            f"{model.params[name]:.4g}",
            f"[{ci[0]:.3g}, {ci[1]:.3g}]",
            f"{model.pvalues[name]:.4f}",
        ])

    f_p = float(model.f_pvalue)
    verdict = "explains a statistically significant" if f_p < alpha else "does not explain a statistically significant"
    freq = frequentist_block(
        statistic_name="F",
        statistic_value=model.fvalue,
        p_value=f_p,
        df=f"{int(model.df_model)}, {int(model.df_resid)}",
        estimate=estimate_block("R²", float(model.rsquared)),
        effect_size=effect_size_block("adjusted R²", "eta2", float(model.rsquared_adj)),
        summary=(
            f"The model {verdict} amount of variation in {outcome}; "
            f"F({int(model.df_model)}, {int(model.df_resid)}) = {model.fvalue:.2f}, p = {f_p:.4f}, "
            f"R² = {model.rsquared:.3f} (adjusted {model.rsquared_adj:.3f})."
        ),
        extra={"coefficients": [
            {"term": r[0], "beta": clean(model.params[n]), "p_value": clean(model.pvalues[n])}
            for r, n in zip(coef_rows, X.columns)
        ]},
    )
    bayes = bayesian_block(available=False, summary="", note=NO_BF_NOTE)

    checks = [A.check_residual_normality(model.resid, alpha),
              A.check_homoscedasticity(model.resid, model.fittedvalues, alpha)]
    if len(num_predictors) >= 2:
        checks.append(A.check_multicollinearity(work[num_predictors]))
    checks.append(A.check_independence())

    return stat_result(
        method="linear_regression",
        method_label="Linear regression (OLS)",
        n_used=len(work),
        n_excluded=0,
        frequentist=freq,
        bayesian=bayes,
        assumptions=checks,
        tables=[{"title": "Coefficients",
                 "columns": ["Term", "β", f"{int((1 - alpha) * 100)}% CI", "p"],
                 "rows": coef_rows}],
        groups={"outcome": outcome, "predictors": predictors,
                "fitted": [clean(v) for v in model.fittedvalues],
                "actual": [clean(v) for v in y]},
    )


def logistic_regression(df: pd.DataFrame, variables: dict, params: dict) -> dict:
    outcome = variables["outcome"]
    predictors = variables["predictors"]
    if isinstance(predictors, str):
        predictors = [predictors]
    if not predictors:
        raise AnalysisError("Select at least one predictor.")
    alpha = float(params.get("alpha", 0.05))

    work = df[[outcome, *predictors]].dropna().copy()
    levels = sorted(work[outcome].astype(str).unique())
    if len(levels) != 2:
        raise AnalysisError(
            f"Logistic regression needs a binary outcome; '{outcome}' has "
            f"{len(levels)} distinct values."
        )
    y = (work[outcome].astype(str) == levels[1]).astype(int)

    cat_predictors = [p for p in predictors if pd.to_numeric(work[p], errors="coerce").notna().mean() < 0.7]
    for p in predictors:
        if p not in cat_predictors:
            work[p] = pd.to_numeric(work[p], errors="coerce")
    work = work.dropna()
    y = y.loc[work.index]
    X = pd.get_dummies(work[predictors], columns=cat_predictors, drop_first=True, dtype=float)
    X = sm.add_constant(X, has_constant="add").astype(float)

    try:
        model = sm.Logit(y, X).fit(disp=False)
    except Exception as exc:  # noqa: BLE001
        raise AnalysisError(f"Logistic regression failed to converge: {exc}") from exc

    ci = model.conf_int(alpha=alpha)
    coef_rows = []
    for name in X.columns:
        coef_rows.append([
            "intercept" if name == "const" else name,
            f"{model.params[name]:.4g}",
            f"{np.exp(model.params[name]):.3g}",
            f"[{np.exp(ci.loc[name][0]):.3g}, {np.exp(ci.loc[name][1]):.3g}]",
            f"{model.pvalues[name]:.4f}",
        ])

    llr_p = float(model.llr_pvalue)
    verdict = "a statistically significant" if llr_p < alpha else "no statistically significant"
    freq = frequentist_block(
        statistic_name="LR χ²",
        statistic_value=float(model.llr),
        p_value=llr_p,
        df=int(model.df_model),
        estimate=estimate_block("McFadden pseudo-R²", float(model.prsquared)),
        summary=(
            f"The logistic model (predicting {outcome} = {levels[1]}) shows {verdict} "
            f"improvement over the null model; LR χ²({int(model.df_model)}) = {model.llr:.2f}, "
            f"p = {llr_p:.4f}, pseudo-R² = {model.prsquared:.3f}."
        ),
        extra={"coefficients": [
            {"term": ("intercept" if n == "const" else n),
             "log_odds": clean(model.params[n]), "odds_ratio": clean(float(np.exp(model.params[n]))),
             "p_value": clean(model.pvalues[n])}
            for n in X.columns
        ], "positive_class": levels[1]},
    )
    bayes = bayesian_block(available=False, summary="", note=NO_BF_NOTE)
    checks = [A.check_independence(),
              A.check_sample_size(int(min(y.sum(), len(y) - y.sum())), 10 * len(X.columns),
                                  "events per predictor rule (≈10×)")]

    return stat_result(
        method="logistic_regression",
        method_label="Logistic regression",
        n_used=len(work),
        n_excluded=0,
        frequentist=freq,
        bayesian=bayes,
        assumptions=checks,
        tables=[{"title": "Coefficients (odds ratios)",
                 "columns": ["Term", "log-odds", "OR", f"{int((1 - alpha) * 100)}% CI (OR)", "p"],
                 "rows": coef_rows}],
        groups={"outcome": outcome, "positive_class": levels[1], "predictors": predictors},
    )
