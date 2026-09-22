import numpy as np
import pandas as pd

from app.services.stats import run_analysis


def test_unknown_method_is_structured_failure(sample_df):
    out = run_analysis(sample_df, "not_a_method", {})
    assert out["status"] == "failed"
    assert "Unknown analysis method" in out["error"]


def test_missing_role_is_structured_failure(sample_df):
    out = run_analysis(sample_df, "independent_ttest", {"outcome": "systolic_bp"})
    assert out["status"] == "failed"
    assert "group" in out["error"]


def test_wrong_dtype_is_rejected(sample_df):
    out = run_analysis(sample_df, "pearson",
                       {"variable_1": "systolic_bp", "variable_2": "sex"})
    assert out["status"] == "failed"
    assert "sex" in out["error"]


def test_group_with_three_levels_rejected_for_ttest(sample_df):
    out = run_analysis(sample_df, "independent_ttest",
                       {"outcome": "systolic_bp", "group": "year_group"})
    assert out["status"] == "failed"


def test_listwise_deletion_counts_excluded(sample_df):
    df = sample_df.copy()
    df.loc[:9, "systolic_bp"] = np.nan
    out = run_analysis(df, "independent_ttest",
                       {"outcome": "systolic_bp", "group": "activity_level"})
    assert out["status"] == "complete"
    assert out["result"]["n_used"] == len(df) - 10
    assert out["result"]["n_excluded"] == 10


def test_same_column_two_roles_rejected(sample_df):
    out = run_analysis(sample_df, "pearson",
                       {"variable_1": "bmi", "variable_2": "bmi"})
    assert out["status"] == "failed"


def test_all_missing_outcome_is_graceful(sample_df):
    df = sample_df.copy()
    df["systolic_bp"] = np.nan
    out = run_analysis(df, "independent_ttest",
                       {"outcome": "systolic_bp", "group": "activity_level"})
    assert out["status"] == "failed"
    assert out["result"] is None
