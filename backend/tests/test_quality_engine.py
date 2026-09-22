import numpy as np
import pandas as pd

from app.services.quality_engine import (
    detect_duplicates,
    detect_invalid_values,
    detect_outliers,
    profile_dataset,
    run_quality_report,
)
from app.services.type_inference import classify_column, infer_all_types


def test_classify_column_numeric_dtype():
    info = classify_column(pd.Series([1, 2, 3, 4, 5]), "age")
    assert info.dtype == "numeric"
    assert info.is_numeric_like


def test_classify_column_binary():
    info = classify_column(pd.Series([0, 1, 0, 1, 1]), "flag")
    assert info.dtype == "binary"


def test_classify_column_categorical_text():
    info = classify_column(
        pd.Series(["Active", "Inactive", "Unknown", "Active", "Inactive"]), "activity_level"
    )
    assert info.dtype == "categorical"


def test_classify_column_two_levels_is_binary_not_categorical():
    # Exactly 2 distinct values is treated as binary/dichotomous regardless of
    # whether the levels are text or numeric — matches the statistical convention.
    info = classify_column(pd.Series(["Active", "Inactive", "Active", "Active"]), "activity_level")
    assert info.dtype == "binary"


def test_classify_column_identifier():
    info = classify_column(pd.Series([f"P{i}" for i in range(50)]), "participant_id")
    assert info.dtype == "identifier"


def test_classify_column_tolerates_lab_censoring_tokens():
    # "<0.005" style values are common in lab data and should not break numeric detection.
    info = classify_column(pd.Series(["<0.005", "0.012", "0.03", "<0.01", "0.02"]), "cn_free")
    assert info.dtype == "numeric"
    assert info.is_numeric_like
    assert info.non_numeric_tokens == []


def test_classify_column_flags_genuine_non_numeric_tokens():
    info = classify_column(pd.Series([1, 2, 3, "unknown", 5, 6, 7, 8]), "systolic_bp")
    assert info.dtype == "numeric"
    assert "unknown" in info.non_numeric_tokens


def test_profile_dataset_reports_missing_and_stats():
    df = pd.DataFrame({"age": [20, 25, None, 30], "sex": ["M", "F", "M", "F"]})
    types = infer_all_types(df)
    profile = profile_dataset(df, types)
    age_col = next(c for c in profile["columns"] if c["name"] == "age")
    assert age_col["missing_count"] == 1
    assert age_col["missing_pct"] == 25.0
    assert age_col["mean"] == 25.0


def test_detect_duplicates_finds_exact_repeats():
    df = pd.DataFrame({"a": [1, 2, 1, 3], "b": ["x", "y", "x", "z"]})
    result = detect_duplicates(df)
    assert result["duplicate_row_count"] == 1
    assert result["example_groups"] == [[0, 2]]


def test_detect_duplicates_empty_when_no_repeats():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    result = detect_duplicates(df)
    assert result["duplicate_row_count"] == 0
    assert result["example_groups"] == []


def test_detect_outliers_flags_extreme_value():
    df = pd.DataFrame({"bmi": [22, 23, 21, 24, 22, 23, 250]})
    types = infer_all_types(df)
    outliers = detect_outliers(df, types)
    assert len(outliers) == 1
    assert outliers[0]["column"] == "bmi"
    assert 250 in outliers[0]["example_values"]


def test_detect_outliers_skips_binary_columns():
    df = pd.DataFrame({"flag": [0, 1, 0, 1, 0, 1]})
    types = infer_all_types(df)
    outliers = detect_outliers(df, types)
    assert outliers == []


def test_detect_invalid_values_flags_out_of_range_ph():
    df = pd.DataFrame({"ph_level": [6.5, 7.0, 6.8, 22.0, 7.2]})
    types = infer_all_types(df)
    invalid = detect_invalid_values(df, types)
    assert any(v["reason"] == "out_of_known_range" and v["column"] == "ph_level" for v in invalid)


def test_detect_invalid_values_flags_non_numeric_tokens():
    df = pd.DataFrame({"score": [1, 2, 3, "N/A", 5, 6, 7, 8]})
    types = infer_all_types(df)
    invalid = detect_invalid_values(df, types)
    match = next(v for v in invalid if v["reason"] == "non_numeric_tokens")
    assert match["count"] == 1
    assert "N/A" in match["examples"]


def test_run_quality_report_clean_dataset_scores_high():
    df = pd.DataFrame(
        {
            "age": [20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
            "sex": ["M", "F"] * 5,
        }
    )
    report = run_quality_report(df)
    assert report["score"]["overall"] >= 95
    assert report["score"]["completeness"] == 100
    assert report["duplicates"]["duplicate_row_count"] == 0


def test_run_quality_report_messy_dataset_scores_lower():
    df = pd.DataFrame(
        {
            "age": [20, None, 22, 999, 24, 25, 26, 27, 28, 29],
            "sex": ["M", "F", "M", "F", "M", "F", "M", "F", "M", "F"],
        }
    )
    # Duplicate the first row to introduce an exact-duplicate record.
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    report = run_quality_report(df)
    assert report["score"]["overall"] < 95
    assert report["duplicates"]["duplicate_row_count"] == 1


def test_run_quality_report_handles_empty_dataframe_without_crashing():
    df = pd.DataFrame({"a": pd.Series(dtype="float64"), "b": pd.Series(dtype="object")})
    report = run_quality_report(df)
    assert report["n_rows"] == 0
    assert report["score"]["overall"] == 100


def test_json_safe_no_nan_or_inf_in_numeric_fields():
    df = pd.DataFrame({"x": [1.0, np.inf, -np.inf, np.nan, 5.0]})
    report = run_quality_report(df)
    col = report["columns"][0]
    for key in ("mean", "median", "std", "min", "max"):
        assert col[key] is None or np.isfinite(col[key])
