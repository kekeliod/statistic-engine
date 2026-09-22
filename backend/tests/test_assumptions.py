import numpy as np

from app.services.stats import assumptions as A


def test_normality_passes_for_normal_data():
    rng = np.random.default_rng(0)
    out = A.check_normality(rng.normal(0, 1, 300), "x")
    assert out["passed"] is True
    assert out["p_value"] > 0.05


def test_normality_fails_for_skewed_data():
    rng = np.random.default_rng(0)
    out = A.check_normality(rng.exponential(1, 300), "x", alternative="the Mann–Whitney U test")
    assert out["passed"] is False
    assert "Mann–Whitney" in out["recommendation"]


def test_normality_undecided_for_tiny_sample():
    out = A.check_normality([1.0, 2.0], "x")
    assert out["passed"] is None


def test_homogeneity_detects_unequal_variance():
    rng = np.random.default_rng(1)
    out = A.check_homogeneity(rng.normal(0, 1, 200), rng.normal(0, 5, 200))
    assert out["passed"] is False


def test_expected_counts_flags_sparse_cells():
    out = A.check_expected_counts(np.array([[2.0, 20.0], [30.0, 40.0]]))
    assert out["passed"] is False
    assert "Fisher" in out["recommendation"]


def test_independence_is_advisory():
    out = A.check_independence()
    assert out["passed"] is None
    assert out["recommendation"]
