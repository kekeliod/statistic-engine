"""Group-comparison tests: t-tests, Mann–Whitney, ANOVA, Kruskal–Wallis, chi-square."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pingouin as pg
from scipy import stats as sps

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
from app.services.stats.methods._shared import (
    ci_pair,
    describe_groups,
    group_levels,
    group_summary_table,
    numeric_series,
    parse_bf10,
)


def _sig(p, alpha):
    return p is not None and p < alpha


def independent_ttest(df: pd.DataFrame, variables: dict, params: dict) -> dict:
    outcome, group = variables["outcome"], variables["group"]
    alpha = float(params.get("alpha", 0.05))
    alternative = params.get("alternative", "two-sided")

    df = df[[outcome, group]].copy()
    df[outcome] = numeric_series(df, outcome)
    df = df.dropna()
    levels = group_levels(df, group, min_groups=2, max_groups=2)
    a = df.loc[df[group] == levels[0], outcome].astype(float)
    b = df.loc[df[group] == levels[1], outcome].astype(float)
    if len(a) < 2 or len(b) < 2:
        raise AnalysisError("Each group needs at least 2 observations for a t-test.")

    res = pg.ttest(a, b, paired=False, alternative=alternative, correction="auto").iloc[0]
    lo, hi = ci_pair(res["CI95"])
    mean_diff = float(a.mean() - b.mean())
    p = float(res["p_val"])
    d = float(res["cohen_d"])
    bf10 = parse_bf10(res["BF10"])

    groups = describe_groups(df, outcome, group)
    verdict = "a statistically significant" if _sig(p, alpha) else "no statistically significant"
    freq = frequentist_block(
        statistic_name="t",
        statistic_value=res["T"],
        p_value=p,
        df=res["dof"],
        estimate=estimate_block(f"mean difference ({levels[0]} − {levels[1]})", mean_diff, lo, hi),
        effect_size=effect_size_block("Cohen's d", "d", d),
        summary=(
            f"Welch's independent t-test found {verdict} difference in {outcome} between "
            f"{group} = {levels[0]} (M = {groups[str(levels[0])]['mean']:.3g}) and "
            f"{levels[1]} (M = {groups[str(levels[1])]['mean']:.3g}); "
            f"t({res['dof']:.1f}) = {res['T']:.2f}, p = {p:.4f}."
        ),
    )
    bayes = bayesian_block(
        available=bf10 is not None,
        bayes_factor_10=bf10,
        prior="Cauchy(0, 0.707) on the standardised effect size (pingouin/JZS default)",
        summary=(
            f"BF10 = {bf10:.3g}: the data are {bf10:.3g}× more likely under a difference "
            f"than under no difference." if bf10 is not None else ""
        ),
        note=None if bf10 is not None else NO_BF_NOTE,
    )
    checks = [
        A.check_normality(a, f"{group} = {levels[0]}", alpha, "the Mann–Whitney U test"),
        A.check_normality(b, f"{group} = {levels[1]}", alpha, "the Mann–Whitney U test"),
        A.check_homogeneity(a, b, alpha=alpha, alternative="the Mann–Whitney U test"),
        A.check_independence(),
    ]
    return stat_result(
        method="independent_ttest",
        method_label="Independent-samples t-test (Welch)",
        n_used=len(df),
        n_excluded=0,
        frequentist=freq,
        bayesian=bayes,
        assumptions=checks,
        tables=[group_summary_table(groups, outcome)],
        groups={"outcome": outcome, "group": group, "levels": [str(x) for x in levels], "stats": groups},
    )


def paired_ttest(df: pd.DataFrame, variables: dict, params: dict) -> dict:
    m1, m2 = variables["measure_1"], variables["measure_2"]
    alpha = float(params.get("alpha", 0.05))
    alternative = params.get("alternative", "two-sided")

    work = df[[m1, m2]].copy()
    work[m1] = pd.to_numeric(work[m1], errors="coerce")
    work[m2] = pd.to_numeric(work[m2], errors="coerce")
    work = work.dropna()
    if len(work) < 3:
        raise AnalysisError("A paired t-test needs at least 3 complete pairs.")

    x, y = work[m1].astype(float), work[m2].astype(float)
    res = pg.ttest(x, y, paired=True, alternative=alternative).iloc[0]
    lo, hi = ci_pair(res["CI95"])
    diff = x - y
    p = float(res["p_val"])
    bf10 = parse_bf10(res["BF10"])
    verdict = "a statistically significant" if _sig(p, alpha) else "no statistically significant"

    freq = frequentist_block(
        statistic_name="t",
        statistic_value=res["T"],
        p_value=p,
        df=res["dof"],
        estimate=estimate_block(f"mean of ({m1} − {m2})", float(diff.mean()), lo, hi),
        effect_size=effect_size_block("Cohen's d (paired)", "d", float(res["cohen_d"])),
        summary=(
            f"Paired t-test found {verdict} mean change from {m2} (M = {y.mean():.3g}) to "
            f"{m1} (M = {x.mean():.3g}); t({res['dof']:.0f}) = {res['T']:.2f}, p = {p:.4f}."
        ),
    )
    bayes = bayesian_block(
        available=bf10 is not None,
        bayes_factor_10=bf10,
        prior="Cauchy(0, 0.707) on the standardised mean difference (pingouin/JZS default)",
        summary=(f"BF10 = {bf10:.3g}." if bf10 is not None else ""),
        note=None if bf10 is not None else NO_BF_NOTE,
    )
    checks = [
        A.check_normality(diff, "the paired differences", alpha, "the Wilcoxon signed-rank test"),
        A.check_independence("Each pair is assumed to come from a distinct, independent unit."),
    ]
    return stat_result(
        method="paired_ttest",
        method_label="Paired-samples t-test",
        n_used=len(work),
        n_excluded=0,
        frequentist=freq,
        bayesian=bayes,
        assumptions=checks,
        tables=[{
            "title": "Paired summary",
            "columns": ["Measure", "n", "Mean", "SD"],
            "rows": [
                [m1, len(x), f"{x.mean():.4g}", f"{x.std(ddof=1):.4g}"],
                [m2, len(y), f"{y.mean():.4g}", f"{y.std(ddof=1):.4g}"],
                ["Difference", len(diff), f"{diff.mean():.4g}", f"{diff.std(ddof=1):.4g}"],
            ],
        }],
        groups={"paired": [m1, m2]},
    )


def mann_whitney(df: pd.DataFrame, variables: dict, params: dict) -> dict:
    outcome, group = variables["outcome"], variables["group"]
    alpha = float(params.get("alpha", 0.05))
    alternative = params.get("alternative", "two-sided")

    work = df[[outcome, group]].copy()
    work[outcome] = numeric_series(work, outcome)
    work = work.dropna()
    levels = group_levels(work, group, min_groups=2, max_groups=2)
    a = work.loc[work[group] == levels[0], outcome].astype(float)
    b = work.loc[work[group] == levels[1], outcome].astype(float)
    if len(a) < 2 or len(b) < 2:
        raise AnalysisError("Each group needs at least 2 observations.")

    res = pg.mwu(a, b, alternative=alternative).iloc[0]
    p = float(res["p_val"])
    rbc = float(res["RBC"])
    groups = describe_groups(work, outcome, group)
    verdict = "a statistically significant" if _sig(p, alpha) else "no statistically significant"

    freq = frequentist_block(
        statistic_name="U",
        statistic_value=res["U_val"],
        p_value=p,
        estimate=estimate_block(
            f"median difference ({levels[0]} − {levels[1]})",
            float(a.median() - b.median()),
        ),
        effect_size=effect_size_block("rank-biserial correlation", "r", rbc),
        summary=(
            f"Mann–Whitney U test found {verdict} difference in the distribution of {outcome} "
            f"between {group} = {levels[0]} (Mdn = {a.median():.3g}) and {levels[1]} "
            f"(Mdn = {b.median():.3g}); U = {res['U_val']:.0f}, p = {p:.4f}. "
            f"CLES = {res['CLES']:.2f}."
        ),
    )
    bayes = bayesian_block(available=False, summary="", note=NO_BF_NOTE)
    checks = [
        A.check_sample_size(min(len(a), len(b)), 5, "smaller group"),
        A.check_independence(),
    ]
    return stat_result(
        method="mann_whitney",
        method_label="Mann–Whitney U test",
        n_used=len(work),
        n_excluded=0,
        frequentist=freq,
        bayesian=bayes,
        assumptions=checks,
        tables=[group_summary_table(groups, outcome)],
        groups={"outcome": outcome, "group": group, "levels": [str(x) for x in levels], "stats": groups},
    )


def one_way_anova(df: pd.DataFrame, variables: dict, params: dict) -> dict:
    outcome, group = variables["outcome"], variables["group"]
    alpha = float(params.get("alpha", 0.05))

    work = df[[outcome, group]].copy()
    work[outcome] = numeric_series(work, outcome)
    work = work.dropna()
    work[group] = work[group].astype(str)
    levels = group_levels(work, group, min_groups=3)
    if (work.groupby(group).size() < 2).any():
        raise AnalysisError("Every group needs at least 2 observations for ANOVA.")

    aov = pg.anova(data=work, dv=outcome, between=group, detailed=False).iloc[0]
    p = float(aov["p_unc"])
    eta2 = float(aov["np2"])
    verdict = "a statistically significant" if _sig(p, alpha) else "no statistically significant"

    try:
        tuk = pg.pairwise_tukey(data=work, dv=outcome, between=group)
        tukey_rows = [
            [f"{r.A} vs {r.B}", f"{r['diff']:.4g}", f"{r['p-tukey']:.4f}"]
            for _, r in tuk.iterrows()
        ]
    except Exception:  # noqa: BLE001
        tukey_rows = []

    groups = describe_groups(work, outcome, group)
    freq = frequentist_block(
        statistic_name="F",
        statistic_value=aov["F"],
        p_value=p,
        df=f"{aov['ddof1']:.0f}, {aov['ddof2']:.0f}",
        effect_size=effect_size_block("partial η²", "eta2", eta2),
        summary=(
            f"One-way ANOVA found {verdict} difference in {outcome} across the "
            f"{len(levels)} levels of {group}; F({aov['ddof1']:.0f}, {aov['ddof2']:.0f}) = "
            f"{aov['F']:.2f}, p = {p:.4f}, partial η² = {eta2:.3f}."
        ),
    )
    bayes = bayesian_block(available=False, summary="", note=NO_BF_NOTE)
    group_arrays = [work.loc[work[group] == lvl, outcome].astype(float) for lvl in levels]
    checks = [
        A.check_homogeneity(*group_arrays, alpha=alpha, alternative="the Kruskal–Wallis test or Welch ANOVA"),
        A.check_normality(
            np.concatenate([g - g.mean() for g in group_arrays]),
            "the residuals", alpha, "the Kruskal–Wallis test",
        ),
        A.check_independence(),
    ]
    tables = [group_summary_table(groups, outcome)]
    if tukey_rows:
        tables.append({"title": "Tukey post-hoc pairwise comparisons",
                       "columns": ["Comparison", "Mean diff", "p (Tukey)"], "rows": tukey_rows})
    return stat_result(
        method="one_way_anova",
        method_label="One-way ANOVA",
        n_used=len(work),
        n_excluded=0,
        frequentist=freq,
        bayesian=bayes,
        assumptions=checks,
        tables=tables,
        groups={"outcome": outcome, "group": group, "levels": [str(x) for x in levels], "stats": groups},
    )


def kruskal_wallis(df: pd.DataFrame, variables: dict, params: dict) -> dict:
    outcome, group = variables["outcome"], variables["group"]
    alpha = float(params.get("alpha", 0.05))

    work = df[[outcome, group]].copy()
    work[outcome] = numeric_series(work, outcome)
    work = work.dropna()
    work[group] = work[group].astype(str)
    levels = group_levels(work, group, min_groups=3)

    res = pg.kruskal(data=work, dv=outcome, between=group).iloc[0]
    H = float(res["H"])
    p = float(res["p_unc"])
    k = len(levels)
    n = len(work)
    eps2 = (H - k + 1) / (n - k) if n > k else None
    verdict = "a statistically significant" if _sig(p, alpha) else "no statistically significant"

    groups = describe_groups(work, outcome, group)
    freq = frequentist_block(
        statistic_name="H",
        statistic_value=H,
        p_value=p,
        df=res["ddof1"],
        effect_size=effect_size_block("epsilon²", "eta2", eps2),
        summary=(
            f"Kruskal–Wallis test found {verdict} difference in {outcome} across the "
            f"{k} levels of {group}; H({res['ddof1']:.0f}) = {H:.2f}, p = {p:.4f}."
        ),
    )
    bayes = bayesian_block(available=False, summary="", note=NO_BF_NOTE)
    checks = [A.check_sample_size(int(work.groupby(group).size().min()), 5, "smallest group"),
              A.check_independence()]
    return stat_result(
        method="kruskal_wallis",
        method_label="Kruskal–Wallis H test",
        n_used=n,
        n_excluded=0,
        frequentist=freq,
        bayesian=bayes,
        assumptions=checks,
        tables=[group_summary_table(groups, outcome)],
        groups={"outcome": outcome, "group": group, "levels": [str(x) for x in levels], "stats": groups},
    )


def chi_square(df: pd.DataFrame, variables: dict, params: dict) -> dict:
    v1, v2 = variables["variable_1"], variables["variable_2"]
    alpha = float(params.get("alpha", 0.05))

    work = df[[v1, v2]].dropna().astype(str)
    if work[v1].nunique() < 2 or work[v2].nunique() < 2:
        raise AnalysisError("Both variables need at least 2 categories for a chi-square test.")

    expected, observed, stats = pg.chi2_independence(work, x=v1, y=v2)
    row = stats[stats["test"] == "pearson"].iloc[0]
    chi2, dof, p, cramer = float(row["chi2"]), float(row["dof"]), float(row["pval"]), float(row["cramer"])
    verdict = "a statistically significant" if (p < alpha) else "no statistically significant"

    ct = pd.crosstab(work[v1], work[v2])
    table = {
        "title": f"Contingency table: {v1} × {v2}",
        "columns": [v1] + [str(c) for c in ct.columns],
        "rows": [[str(idx)] + [int(x) for x in r] for idx, r in ct.iterrows()],
    }
    freq = frequentist_block(
        statistic_name="χ²",
        statistic_value=chi2,
        p_value=p,
        df=dof,
        effect_size=effect_size_block("Cramér's V", "cramer", cramer),
        summary=(
            f"Pearson chi-square test of independence found {verdict} association between "
            f"{v1} and {v2}; χ²({dof:.0f}) = {chi2:.2f}, p = {p:.4f}, Cramér's V = {cramer:.3f}."
        ),
    )
    bayes = bayesian_block(available=False, summary="", note=NO_BF_NOTE)
    checks = [A.check_expected_counts(expected.values), A.check_independence()]
    return stat_result(
        method="chi_square",
        method_label="Chi-square test of independence",
        n_used=len(work),
        n_excluded=0,
        frequentist=freq,
        bayesian=bayes,
        assumptions=checks,
        tables=[table],
        groups={"crosstab": {"index": v1, "columns": v2,
                             "counts": {str(i): {str(c): int(v) for c, v in r.items()}
                                        for i, r in ct.iterrows()}}},
    )
