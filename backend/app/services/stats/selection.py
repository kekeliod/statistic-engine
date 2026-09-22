"""Rule-based analysis recommender.

Maps a research objective (free text) + the dataset's columns to a ranked list of
suggested methods, with a short rationale and a guess at which columns fill each
role. Used directly when no Anthropic API key is configured, and as the candidate
generator / fallback for the AI recommender (Slice B).

This is deliberately transparent keyword logic, not ML. It errs toward suggesting
*something* runnable and explaining the reasoning so the researcher can correct it.
"""
from __future__ import annotations

import re

COMPARE_WORDS = {"compare", "comparison", "difference", "differ", "differs", "between",
                 "versus", "vs", "higher", "lower", "greater", "effect of", "impact of"}
RELATE_WORDS = {"association", "associated", "associate", "relationship", "related", "relate",
                "correlate", "correlation", "influence", "linked", "link between"}
DESCRIBE_WORDS = {"average", "mean ", "median", "describe", "description", "distribution",
                  "summary", "summarise", "summarize", "proportion", "prevalence", "frequency",
                  "determine the", "what is the", "estimate the"}
PREDICT_WORDS = {"predict", "predictor", "determinant", "factor", "factors", "explain",
                 "explains", "explained by", "driver", "drivers", "which variables"}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


# Common phrasings that map onto abbreviated column names. A phrase on the left,
# found in an objective, counts as a mention of any column whose name contains a
# token on the right.
_SYNONYMS: list[tuple[str, tuple[str, ...]]] = [
    ("blood pressure", ("bp",)),
    ("body mass index", ("bmi",)),
    ("physical activity", ("activity",)),
    ("heart rate", ("hr", "pulse")),
    ("body weight", ("weight", "mass")),
]

# name tokens too short/common to match on their own
_WEAK_TOKENS = {"id", "no", "code", "level", "type", "group", "value", "score", "rate"}


def _column_dtypes(profile: dict) -> dict[str, str]:
    return {c["name"]: c["dtype"] for c in profile.get("columns", [])}


def _column_values(profile: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in profile.get("columns", []):
        tv = c.get("top_values") or []
        out[c["name"]] = [str(t["value"]).lower() for t in tv]
    return out


def _match_columns(objective: str, columns: list[str]) -> set[str]:
    """Columns whose name (or a synonym / distinctive word part) appears in the objective."""
    obj = objective.lower()
    obj_tokens = set(_tokens(objective))
    # expand with synonym-implied tokens
    implied: set[str] = set()
    for phrase, targets in _SYNONYMS:
        if phrase in obj:
            implied.update(targets)

    hits: set[str] = set()
    for col in columns:
        parts = _tokens(col)
        if not parts:
            continue
        strong = [p for p in parts if p not in _WEAK_TOKENS]
        if len(parts) >= 2 and " ".join(parts) in obj:
            hits.add(col)
        elif all(p in obj_tokens for p in parts):
            hits.add(col)
        elif len(parts) >= 2 and sum(p in obj_tokens for p in parts) >= 2:
            hits.add(col)
        elif implied and any(p in implied for p in parts):
            hits.add(col)
        elif any(p in obj_tokens for p in strong if len(p) >= 5):
            hits.add(col)
    return hits


def _match_by_values(objective: str, values: dict[str, list[str]]) -> set[str]:
    """Categorical/binary columns whose level labels appear in the objective."""
    obj_tokens = set(_tokens(objective))
    hits: set[str] = set()
    for col, levels in values.items():
        for lvl in levels:
            lvl_tokens = _tokens(lvl)
            if lvl_tokens and all(t in obj_tokens for t in lvl_tokens):
                hits.add(col)
                break
    return hits


def _has(text: str, words: set[str]) -> bool:
    t = text.lower()
    return any(w in t for w in words)


def _rec(objective_index, objective, method_key, method_label, rationale, confidence,
         suggested_variables, chart_suggestion, alternative=None):
    return {
        "objective_index": objective_index,
        "objective_text": objective,
        "method_key": method_key,
        "method_label": method_label,
        "rationale": rationale,
        "confidence": confidence,
        "suggested_variables": suggested_variables,
        "chart_suggestion": chart_suggestion,
        "alternative_method_key": alternative,
        "source": "rules",
    }


def recommend_for_objective(objective_index: int, objective: str, profile: dict) -> list[dict]:
    dtypes = _column_dtypes(profile)
    columns = list(dtypes)
    values = _column_values(profile)

    matched = _match_columns(objective, columns) | _match_by_values(objective, values)
    m_numeric = [c for c in columns if c in matched and dtypes.get(c) == "numeric"]
    m_binary = [c for c in columns if c in matched and dtypes.get(c) == "binary"]
    m_categ = [c for c in columns if c in matched and dtypes.get(c) == "categorical"]
    any_numeric = [c for c in columns if dtypes.get(c) == "numeric"]
    any_binary = [c for c in columns if dtypes.get(c) == "binary"]
    any_categ = [c for c in columns if dtypes.get(c) == "categorical"]

    wants_compare = _has(objective, COMPARE_WORDS)
    wants_relate = _has(objective, RELATE_WORDS)
    wants_describe = _has(objective, DESCRIBE_WORDS)
    wants_predict = _has(objective, PREDICT_WORDS)

    recs: list[dict] = []
    m_groups = m_binary + m_categ

    # ---- 1. prediction / regression ----
    if wants_predict and m_numeric:
        outcome = m_numeric[0]
        preds = [c for c in (m_numeric[1:] + m_binary + m_categ) if c != outcome]
        if not preds:
            preds = [c for c in (any_numeric + any_binary + any_categ) if c != outcome][:3]
        if preds:
            recs.append(_rec(
                objective_index, objective, "linear_regression", "Linear regression (OLS)",
                f"The objective asks which variables predict/explain '{outcome}'. Linear "
                f"regression quantifies how {', '.join(preds)} jointly relate to it.",
                "high" if m_numeric else "medium",
                {"outcome": outcome, "predictors": preds}, "actual-vs-predicted scatter",
            ))
    elif wants_predict and m_binary:
        outcome = m_binary[0]
        preds = [c for c in (m_numeric + m_categ) if c != outcome] or \
                [c for c in (any_numeric + any_categ) if c != outcome][:3]
        if preds:
            recs.append(_rec(
                objective_index, objective, "logistic_regression", "Logistic regression",
                f"The objective seeks predictors of the binary outcome '{outcome}'. Logistic "
                f"regression estimates how {', '.join(preds)} change its odds.",
                "high", {"outcome": outcome, "predictors": preds}, "coefficient (odds ratio) plot",
            ))

    # ---- 2. association between two categorical variables ----
    # (checked before the group comparison: if the objective names two categoricals
    #  and no numeric, it is a categorical-vs-categorical question)
    if not recs and (wants_relate or wants_compare) and len(m_groups) >= 2 and not m_numeric:
        recs.append(_rec(
            objective_index, objective, "chi_square", "Chi-square test of independence",
            f"The objective asks whether '{m_groups[0]}' and '{m_groups[1]}' are associated. "
            "Both are categorical, so a chi-square test of independence applies.",
            "high", {"variable_1": m_groups[0], "variable_2": m_groups[1]}, "grouped bar chart",
        ))

    # ---- 3. group comparison when BOTH a numeric and a group column are named ----
    # (a "does X relate to Y" objective where one side is categorical is a group
    #  comparison, not a numeric-numeric correlation)
    if not recs and (wants_compare or wants_relate) and m_numeric and m_groups:
        outcome, group = m_numeric[0], m_groups[0]
        n_levels = next((c.get("unique_count") for c in profile["columns"] if c["name"] == group), 0)
        if group in m_binary or (n_levels and n_levels <= 2):
            recs.append(_rec(
                objective_index, objective, "independent_ttest", "Independent-samples t-test",
                f"The objective links '{outcome}' with the two groups of '{group}'. An "
                "independent-samples t-test compares the group means.",
                "high", {"outcome": outcome, "group": group}, "grouped box plot",
                alternative="mann_whitney",
            ))
        else:
            recs.append(_rec(
                objective_index, objective, "one_way_anova", "One-way ANOVA",
                f"The objective links '{outcome}' with the {n_levels or 'several'} categories of "
                f"'{group}'. One-way ANOVA compares means across the groups.",
                "high", {"outcome": outcome, "group": group}, "grouped box plot",
                alternative="kruskal_wallis",
            ))

    # ---- 4. correlation between two numeric variables ----
    if not recs and wants_relate and len(m_numeric) >= 2:
        recs.append(_rec(
            objective_index, objective, "pearson", "Pearson correlation",
            f"The objective asks about the relationship between two numeric variables "
            f"('{m_numeric[0]}' and '{m_numeric[1]}'). Pearson correlation quantifies a linear association.",
            "high", {"variable_1": m_numeric[0], "variable_2": m_numeric[1]},
            "scatter plot with fit line", alternative="spearman",
        ))

    # ---- 5. group comparison fallback (numeric named, group inferred) ----
    if not recs and (wants_compare or wants_relate) and (m_numeric or (wants_compare and any_numeric)):
        outcome = (m_numeric or any_numeric)[0]
        group = None
        kind = "binary"
        conf = "high" if m_numeric else "medium"
        if m_binary:
            group, kind = m_binary[0], "binary"
        elif m_categ:
            group, kind = m_categ[0], "categorical"
        elif any_binary:
            group, kind, conf = any_binary[0], "binary", "medium"
        elif any_categ:
            group, kind, conf = any_categ[0], "categorical", "medium"
        if group:
            n_levels = next((c.get("unique_count") for c in profile["columns"] if c["name"] == group), 0)
            if kind == "binary" or (n_levels and n_levels <= 2):
                recs.append(_rec(
                    objective_index, objective, "independent_ttest", "Independent-samples t-test",
                    f"The objective compares '{outcome}' between the two groups of '{group}'. "
                    "An independent-samples t-test compares the group means.",
                    conf, {"outcome": outcome, "group": group}, "grouped box plot",
                    alternative="mann_whitney",
                ))
            else:
                recs.append(_rec(
                    objective_index, objective, "one_way_anova", "One-way ANOVA",
                    f"The objective compares '{outcome}' across the {n_levels or 'several'} "
                    f"categories of '{group}'. One-way ANOVA compares means across 3+ groups.",
                    conf, {"outcome": outcome, "group": group}, "grouped box plot",
                    alternative="kruskal_wallis",
                ))

    # ---- 6. description / fallback ----
    if not recs or wants_describe:
        targets = (m_numeric + m_binary + m_categ) or matched_list(matched, columns) \
            or (any_numeric[:2] + any_categ[:1])
        if targets:
            recs.append(_rec(
                objective_index, objective, "descriptive", "Descriptive statistics",
                ("The objective asks for a summary value (average / distribution), which "
                 "descriptive statistics provide directly."
                 if wants_describe else
                 "No clear comparison or relationship was detected for this objective, so "
                 "start by summarising the relevant variables."),
                "high" if wants_describe else "low",
                {"variables": targets}, "histogram",
            ))

    seen, unique = set(), []
    for r in recs:
        if r["method_key"] in seen:
            continue
        seen.add(r["method_key"])
        unique.append(r)
    return unique


def matched_list(matched: set[str], columns: list[str]) -> list[str]:
    return [c for c in columns if c in matched]


def recommend_analyses(project, profile: dict) -> list[dict]:
    objectives = list(getattr(project, "objectives", []) or [])
    out: list[dict] = []
    if not objectives:
        cols = [c["name"] for c in profile.get("columns", [])]
        out.append(_rec(None, "(no objective specified)", "descriptive", "Descriptive statistics",
                        "Add research objectives to get targeted recommendations. In the "
                        "meantime, a descriptive overview of every variable is a good start.",
                        "low", {"variables": cols[:6]}, "histogram"))
        return out
    for i, obj in enumerate(objectives):
        out.extend(recommend_for_objective(i, obj, profile))
    return out
