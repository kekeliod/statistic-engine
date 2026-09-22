"""Registry of available statistical methods.

Each entry declares the roles the method needs (with arity and the column dtypes
that make sense for that role), its default parameters, and the callable that
runs it. The frontend method picker, the AI tool schema (Slice B), and the
recommendation engine all read from here so there is a single source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from app.services.stats.base import AnalysisError
from app.services.stats.methods import comparison, correlation, descriptive, regression


@dataclass(frozen=True)
class Role:
    name: str
    arity: str  # "one" | "many"
    dtypes: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class MethodSpec:
    key: str
    label: str
    category: str  # descriptive | comparison | correlation | regression | association
    description: str
    when_to_use: str
    roles: tuple[Role, ...]
    param_defaults: dict
    runner: Callable
    bayesian_supported: bool  # True when pingouin returns a Bayes factor for this test


_ALPHA = {"alpha": 0.05}
_ALPHA_ALT = {"alpha": 0.05, "alternative": "two-sided"}


METHODS: dict[str, MethodSpec] = {
    "descriptive": MethodSpec(
        key="descriptive", label="Descriptive statistics", category="descriptive",
        description="Mean, median, SD, IQR, range for numeric variables; counts and percentages for categories.",
        when_to_use="Summarise the sample and answer 'what is the average / distribution of X?'.",
        roles=(Role("variables", "many", ("numeric", "binary", "categorical", "ordinal"),
                    "One or more variables to summarise"),),
        param_defaults={}, runner=descriptive.describe, bayesian_supported=False,
    ),
    "independent_ttest": MethodSpec(
        key="independent_ttest", label="Independent-samples t-test", category="comparison",
        description="Compares the mean of a numeric outcome between two independent groups (Welch's version).",
        when_to_use="Compare a numeric outcome between exactly two unrelated groups.",
        roles=(
            Role("outcome", "one", ("numeric",), "Numeric outcome to compare"),
            Role("group", "one", ("binary",), "Two-level grouping variable"),
        ),
        param_defaults=dict(_ALPHA_ALT), runner=comparison.independent_ttest, bayesian_supported=True,
    ),
    "paired_ttest": MethodSpec(
        key="paired_ttest", label="Paired-samples t-test", category="comparison",
        description="Compares two numeric measurements taken on the same units (e.g. before / after).",
        when_to_use="Compare two related numeric measurements on the same participants.",
        roles=(
            Role("measure_1", "one", ("numeric",), "First measurement (e.g. post)"),
            Role("measure_2", "one", ("numeric",), "Second measurement (e.g. pre)"),
        ),
        param_defaults=dict(_ALPHA_ALT), runner=comparison.paired_ttest, bayesian_supported=True,
    ),
    "mann_whitney": MethodSpec(
        key="mann_whitney", label="Mann–Whitney U test", category="comparison",
        description="Non-parametric comparison of a numeric outcome's distribution between two groups.",
        when_to_use="Two-group comparison when the outcome is skewed, ordinal, or the t-test assumptions fail.",
        roles=(
            Role("outcome", "one", ("numeric", "ordinal"), "Numeric or ordinal outcome"),
            Role("group", "one", ("binary",), "Two-level grouping variable"),
        ),
        param_defaults=dict(_ALPHA_ALT), runner=comparison.mann_whitney, bayesian_supported=False,
    ),
    "one_way_anova": MethodSpec(
        key="one_way_anova", label="One-way ANOVA", category="comparison",
        description="Compares the mean of a numeric outcome across three or more independent groups.",
        when_to_use="Compare a numeric outcome across 3+ unrelated groups.",
        roles=(
            Role("outcome", "one", ("numeric",), "Numeric outcome"),
            Role("group", "one", ("categorical", "binary"), "Grouping variable (3+ levels)"),
        ),
        param_defaults=dict(_ALPHA), runner=comparison.one_way_anova, bayesian_supported=False,
    ),
    "kruskal_wallis": MethodSpec(
        key="kruskal_wallis", label="Kruskal–Wallis H test", category="comparison",
        description="Non-parametric comparison of a numeric outcome across three or more groups.",
        when_to_use="3+ group comparison when ANOVA assumptions fail or the outcome is ordinal.",
        roles=(
            Role("outcome", "one", ("numeric", "ordinal"), "Numeric or ordinal outcome"),
            Role("group", "one", ("categorical", "binary"), "Grouping variable (3+ levels)"),
        ),
        param_defaults=dict(_ALPHA), runner=comparison.kruskal_wallis, bayesian_supported=False,
    ),
    "chi_square": MethodSpec(
        key="chi_square", label="Chi-square test of independence", category="association",
        description="Tests whether two categorical variables are associated.",
        when_to_use="Check whether two categorical variables are related (e.g. sex × activity level).",
        roles=(
            Role("variable_1", "one", ("categorical", "binary"), "First categorical variable"),
            Role("variable_2", "one", ("categorical", "binary"), "Second categorical variable"),
        ),
        param_defaults=dict(_ALPHA), runner=comparison.chi_square, bayesian_supported=False,
    ),
    "pearson": MethodSpec(
        key="pearson", label="Pearson correlation", category="correlation",
        description="Strength and direction of a linear relationship between two numeric variables.",
        when_to_use="Measure how two numeric variables move together, assuming a roughly linear relationship.",
        roles=(
            Role("variable_1", "one", ("numeric",), "First numeric variable"),
            Role("variable_2", "one", ("numeric",), "Second numeric variable"),
        ),
        param_defaults=dict(_ALPHA), runner=correlation.pearson, bayesian_supported=True,
    ),
    "spearman": MethodSpec(
        key="spearman", label="Spearman rank correlation", category="correlation",
        description="Strength and direction of a monotonic relationship between two variables (rank-based).",
        when_to_use="Correlation when the relationship is monotonic but not linear, or data are ordinal/skewed.",
        roles=(
            Role("variable_1", "one", ("numeric", "ordinal"), "First variable"),
            Role("variable_2", "one", ("numeric", "ordinal"), "Second variable"),
        ),
        param_defaults=dict(_ALPHA), runner=correlation.spearman, bayesian_supported=False,
    ),
    "linear_regression": MethodSpec(
        key="linear_regression", label="Linear regression (OLS)", category="regression",
        description="Models a numeric outcome as a linear function of one or more predictors.",
        when_to_use="Quantify how several predictors jointly relate to a numeric outcome.",
        roles=(
            Role("outcome", "one", ("numeric",), "Numeric outcome to model"),
            Role("predictors", "many", ("numeric", "binary", "categorical"), "One or more predictors"),
        ),
        param_defaults=dict(_ALPHA), runner=regression.linear_regression, bayesian_supported=False,
    ),
    "logistic_regression": MethodSpec(
        key="logistic_regression", label="Logistic regression", category="regression",
        description="Models a binary outcome's probability as a function of one or more predictors (odds ratios).",
        when_to_use="Identify predictors of a yes/no outcome.",
        roles=(
            Role("outcome", "one", ("binary",), "Binary outcome"),
            Role("predictors", "many", ("numeric", "binary", "categorical"), "One or more predictors"),
        ),
        param_defaults=dict(_ALPHA), runner=regression.logistic_regression, bayesian_supported=False,
    ),
}


def get_method(key: str) -> MethodSpec:
    try:
        return METHODS[key]
    except KeyError:
        raise AnalysisError(
            f"Unknown analysis method '{key}'. Available: {', '.join(sorted(METHODS))}."
        ) from None
