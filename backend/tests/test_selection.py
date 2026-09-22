from types import SimpleNamespace

from app.services.quality_engine import run_quality_report
from app.services.stats.selection import recommend_analyses


def _profile(df):
    return run_quality_report(df)


def _methods(recs, obj_idx):
    return [r["method_key"] for r in recs if r["objective_index"] == obj_idx]


def test_recommends_ttest_for_two_group_numeric_comparison(sample_df):
    project = SimpleNamespace(objectives=[
        "Compare systolic bp between active and inactive students",
    ])
    recs = recommend_analyses(project, _profile(sample_df))
    assert "independent_ttest" in _methods(recs, 0)
    ttest = next(r for r in recs if r["method_key"] == "independent_ttest")
    assert ttest["suggested_variables"]["outcome"] == "systolic_bp"
    assert ttest["alternative_method_key"] == "mann_whitney"


def test_recommends_anova_for_multi_group(sample_df):
    project = SimpleNamespace(objectives=["Compare bmi between year group categories"])
    recs = recommend_analyses(project, _profile(sample_df))
    assert "one_way_anova" in _methods(recs, 0)


def test_recommends_correlation_for_relationship_between_numerics(sample_df):
    project = SimpleNamespace(objectives=[
        "Determine whether systolic bp is associated with bmi",
    ])
    recs = recommend_analyses(project, _profile(sample_df))
    assert "pearson" in _methods(recs, 0)


def test_recommends_chi_square_for_two_categoricals(sample_df):
    project = SimpleNamespace(objectives=[
        "Examine the association between sex and year group",
    ])
    recs = recommend_analyses(project, _profile(sample_df))
    assert "chi_square" in _methods(recs, 0)


def test_recommends_regression_for_predictors(sample_df):
    project = SimpleNamespace(objectives=[
        "Identify predictors that explain systolic bp",
    ])
    recs = recommend_analyses(project, _profile(sample_df))
    assert "linear_regression" in _methods(recs, 0)


def test_recommends_descriptive_for_average(sample_df):
    project = SimpleNamespace(objectives=["Determine the average systolic bp of participants"])
    recs = recommend_analyses(project, _profile(sample_df))
    assert "descriptive" in _methods(recs, 0)


def test_no_objectives_falls_back_to_descriptive(sample_df):
    recs = recommend_analyses(SimpleNamespace(objectives=[]), _profile(sample_df))
    assert recs and recs[0]["method_key"] == "descriptive"


def test_all_recommendations_are_rule_sourced(sample_df):
    project = SimpleNamespace(objectives=["Compare systolic bp between groups", "describe bmi"])
    recs = recommend_analyses(project, _profile(sample_df))
    assert recs
    assert all(r["source"] == "rules" for r in recs)
