"""Every registry method: runs, matches raw SciPy, and reports Bayesian status correctly."""
import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps

from app.services.stats import run_analysis
from app.services.stats.registry import METHODS


def _ok(df, method, variables, params=None):
    out = run_analysis(df, method, variables, params or {})
    assert out["status"] == "complete", out.get("error")
    return out["result"]


def test_all_methods_present_in_registry():
    assert set(METHODS) == {
        "descriptive", "independent_ttest", "paired_ttest", "mann_whitney",
        "one_way_anova", "kruskal_wallis", "chi_square", "pearson", "spearman",
        "linear_regression", "logistic_regression",
    }


def test_independent_ttest_matches_scipy(sample_df):
    r = _ok(sample_df, "independent_ttest", {"outcome": "systolic_bp", "group": "activity_level"})
    a = sample_df.loc[sample_df.activity_level == "Active", "systolic_bp"]
    b = sample_df.loc[sample_df.activity_level == "Inactive", "systolic_bp"]
    t, p = sps.ttest_ind(a, b, equal_var=False)
    assert r["frequentist"]["statistic"]["value"] == pytest.approx(t, rel=1e-3)
    assert r["frequentist"]["p_value"] == pytest.approx(p, rel=1e-3)
    assert r["bayesian"]["available"] is True
    assert r["bayesian"]["bayes_factor_10"] > 0
    assert r["frequentist"]["effect_size"]["name"] == "Cohen's d"


def test_paired_ttest_matches_scipy(sample_df):
    r = _ok(sample_df, "paired_ttest", {"measure_1": "systolic_bp", "measure_2": "diastolic_bp"})
    t, p = sps.ttest_rel(sample_df.systolic_bp, sample_df.diastolic_bp)
    assert r["frequentist"]["statistic"]["value"] == pytest.approx(t, rel=1e-3)
    assert r["frequentist"]["p_value"] == pytest.approx(p, rel=1e-3)
    assert r["bayesian"]["available"] is True


def test_mann_whitney_matches_scipy_and_has_no_bf(sample_df):
    r = _ok(sample_df, "mann_whitney", {"outcome": "systolic_bp", "group": "activity_level"})
    a = sample_df.loc[sample_df.activity_level == "Active", "systolic_bp"]
    b = sample_df.loc[sample_df.activity_level == "Inactive", "systolic_bp"]
    u, p = sps.mannwhitneyu(a, b, alternative="two-sided")
    assert r["frequentist"]["p_value"] == pytest.approx(p, rel=1e-3)
    assert r["bayesian"]["available"] is False
    assert "does not provide a Bayes factor" in r["bayesian"]["note"]


def test_one_way_anova_matches_scipy_no_bf(sample_df):
    r = _ok(sample_df, "one_way_anova", {"outcome": "bmi", "group": "year_group"})
    groups = [g["bmi"].values for _, g in sample_df.groupby("year_group")]
    f, p = sps.f_oneway(*groups)
    assert r["frequentist"]["statistic"]["value"] == pytest.approx(f, rel=1e-3)
    assert r["frequentist"]["p_value"] == pytest.approx(p, rel=1e-3)
    assert r["bayesian"]["available"] is False
    assert r["frequentist"]["effect_size"]["name"] == "partial η²"


def test_kruskal_matches_scipy(sample_df):
    r = _ok(sample_df, "kruskal_wallis", {"outcome": "bmi", "group": "year_group"})
    groups = [g["bmi"].values for _, g in sample_df.groupby("year_group")]
    h, p = sps.kruskal(*groups)
    assert r["frequentist"]["statistic"]["value"] == pytest.approx(h, rel=1e-3)
    assert r["bayesian"]["available"] is False


def test_chi_square_matches_scipy(sample_df):
    r = _ok(sample_df, "chi_square", {"variable_1": "sex", "variable_2": "year_group"})
    ct = pd.crosstab(sample_df.sex, sample_df.year_group)
    chi2, p, dof, _ = sps.chi2_contingency(ct, correction=False)
    assert r["frequentist"]["statistic"]["value"] == pytest.approx(chi2, rel=1e-3)
    assert r["frequentist"]["p_value"] == pytest.approx(p, rel=1e-3)
    assert r["bayesian"]["available"] is False


def test_pearson_matches_scipy_and_has_bf(sample_df):
    r = _ok(sample_df, "pearson", {"variable_1": "systolic_bp", "variable_2": "bmi"})
    rr, p = sps.pearsonr(sample_df.systolic_bp, sample_df.bmi)
    assert r["frequentist"]["statistic"]["value"] == pytest.approx(rr, rel=1e-3)
    assert r["frequentist"]["p_value"] == pytest.approx(p, rel=1e-3)
    assert r["bayesian"]["available"] is True
    assert r["bayesian"]["bayes_factor_10"] > 0


def test_spearman_matches_scipy_no_bf(sample_df):
    r = _ok(sample_df, "spearman", {"variable_1": "systolic_bp", "variable_2": "bmi"})
    rho, p = sps.spearmanr(sample_df.systolic_bp, sample_df.bmi)
    assert r["frequentist"]["statistic"]["value"] == pytest.approx(rho, rel=1e-3)
    assert r["bayesian"]["available"] is False


def test_linear_regression_matches_numpy(sample_df):
    r = _ok(sample_df, "linear_regression", {"outcome": "systolic_bp", "predictors": ["bmi"]})
    # simple OLS slope/intercept via least squares
    x = sample_df.bmi.values
    y = sample_df.systolic_bp.values
    slope, intercept = np.polyfit(x, y, 1)
    coefs = {c["term"]: c["beta"] for c in r["frequentist"]["coefficients"]}
    assert coefs["bmi"] == pytest.approx(slope, rel=1e-3)
    assert coefs["intercept"] == pytest.approx(intercept, rel=1e-3)
    assert r["bayesian"]["available"] is False


def test_logistic_regression_runs(sample_df):
    r = _ok(sample_df, "logistic_regression",
            {"outcome": "activity_level", "predictors": ["systolic_bp", "bmi"]})
    assert r["frequentist"]["p_value"] is not None
    terms = {c["term"] for c in r["frequentist"]["coefficients"]}
    assert "systolic_bp" in terms
    assert r["bayesian"]["available"] is False


def test_descriptive_reports_numeric_and_categorical(sample_df):
    r = _ok(sample_df, "descriptive", {"variables": ["systolic_bp", "sex"]})
    titles = [t["title"] for t in r["tables"]]
    assert any("numeric" in t.lower() for t in titles)
    assert any("sex" in t for t in titles)
    assert r["frequentist"]["p_value"] is None


def test_result_json_serialisable(sample_df):
    import json
    r = _ok(sample_df, "independent_ttest", {"outcome": "systolic_bp", "group": "activity_level"})
    json.dumps(r)  # must not raise


@pytest.mark.parametrize("method,spec", list(METHODS.items()))
def test_every_method_has_bayesian_block(method, spec, sample_df):
    var_map = {
        "descriptive": {"variables": ["systolic_bp"]},
        "independent_ttest": {"outcome": "systolic_bp", "group": "activity_level"},
        "paired_ttest": {"measure_1": "systolic_bp", "measure_2": "diastolic_bp"},
        "mann_whitney": {"outcome": "systolic_bp", "group": "activity_level"},
        "one_way_anova": {"outcome": "bmi", "group": "year_group"},
        "kruskal_wallis": {"outcome": "bmi", "group": "year_group"},
        "chi_square": {"variable_1": "sex", "variable_2": "year_group"},
        "pearson": {"variable_1": "systolic_bp", "variable_2": "bmi"},
        "spearman": {"variable_1": "systolic_bp", "variable_2": "bmi"},
        "linear_regression": {"outcome": "systolic_bp", "predictors": ["bmi", "age"]},
        "logistic_regression": {"outcome": "activity_level", "predictors": ["systolic_bp"]},
    }[method]
    r = _ok(sample_df, method, var_map)
    b = r["bayesian"]
    assert set(b) >= {"available", "bayes_factor_10", "interpretation", "note"}
    assert b["available"] == spec.bayesian_supported
    if not b["available"]:
        assert b["note"]
