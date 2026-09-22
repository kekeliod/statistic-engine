"""Deterministic statistical analysis engine.

No LLM is involved anywhere in this package. The AI layer (app/services/ai) may
*choose* a method and *explain* a result, but every number is computed here by
pandas / SciPy / statsmodels / pingouin.

Every analysis reports the frequentist and Bayesian views side by side. pingouin
returns a Bayes factor (BF10) from the same call as the p-value for the tests it
supports (t-tests, Pearson correlation); where it does not (ANOVA, chi-square,
non-parametric tests, regression) the result says so explicitly via
``bayesian.available = False`` and a ``bayesian.note`` rather than silently
presenting a frequentist-only answer.
"""

from app.services.stats.execution import run_analysis
from app.services.stats.registry import METHODS, get_method

__all__ = ["run_analysis", "METHODS", "get_method"]
