"""Plain-language interpretation of a statistical result.

`template_interpretation` is deterministic and always available. It keeps the
frequentist and Bayesian statements in separate sentences and never blends the
vocabularies: a p-value is framed as "statistically significant at alpha", a
Bayes factor as "evidence for/against", and neither is called proof of practical
importance. Slice B adds an optional AI polish that must preserve these rules.
"""
from __future__ import annotations

from app.models.project import Project


def _objective_clause(project: Project | None, objective_index: int | None) -> str:
    if project is None or objective_index is None:
        return ""
    objectives = list(project.objectives or [])
    if 0 <= objective_index < len(objectives):
        return f' This addresses the objective: "{objectives[objective_index]}".'
    return ""


def template_interpretation(
    result: dict, project: Project | None = None, objective_index: int | None = None,
    alpha: float = 0.05,
) -> str:
    freq = result.get("frequentist", {})
    bayes = result.get("bayesian", {})
    method_label = result.get("method_label", result.get("method", "The analysis"))
    p = freq.get("p_value")
    es = freq.get("effect_size") or {}
    parts: list[str] = []

    # 1. Frequentist sentence
    if result.get("method") == "descriptive":
        parts.append(freq.get("summary") or f"{method_label} summarised the selected variables.")
    elif p is None:
        parts.append(freq.get("summary") or f"{method_label} was run.")
    else:
        sig = p < alpha
        verb = "is" if sig else "is not"
        parts.append(
            f"{method_label}: the result {verb} statistically significant at the "
            f"α = {alpha:g} level (p = {p:.4f})."
        )
        if es.get("value") is not None:
            mag = es.get("magnitude")
            mag_txt = f", a {mag} effect" if mag else ""
            parts.append(
                f"The estimated effect size ({es['name']}) is {es['value']:.3g}{mag_txt}."
            )
        est = freq.get("estimate") or {}
        if est.get("value") is not None and est.get("ci_low") is not None:
            parts.append(
                f"The {est['name']} is {est['value']:.3g} "
                f"({int(est.get('ci_level', 0.95) * 100)}% CI {est['ci_low']:.3g} to {est['ci_high']:.3g})."
            )

    # 2. Bayesian sentence (kept separate)
    if bayes.get("available") and bayes.get("bayes_factor_10") is not None:
        bf = bayes["bayes_factor_10"]
        strength = bayes.get("interpretation") or ""
        if bf >= 1:
            parts.append(
                f"Bayesian view: the Bayes factor is BF₁₀ = {bf:.3g}, i.e. the data are "
                f"about {bf:.3g}× more likely under an effect than under no effect "
                f"({strength})."
            )
        else:
            parts.append(
                f"Bayesian view: BF₁₀ = {bf:.3g} (BF₀₁ = {1 / bf:.3g}), i.e. the data "
                f"favour no effect ({strength})."
            )
        parts.append("A Bayes factor is not a p-value and does not, by itself, denote 'significance'.")
    else:
        note = bayes.get("note") or "No Bayes factor is available for this test."
        parts.append(f"Bayesian view: {note}")

    # 3. Assumptions caveat
    failed = [a for a in result.get("assumptions", []) if a.get("passed") is False]
    if failed:
        names = "; ".join(
            f"{a['label']}" + (f" — {a['recommendation']}" if a.get("recommendation") else "")
            for a in failed
        )
        parts.append(f"Caution: assumption check(s) not met: {names}")

    # 4. Practical-vs-statistical caveat + objective link
    if p is not None and result.get("method") != "descriptive":
        parts.append(
            "Statistical significance reflects how surprising the data are under the null "
            "hypothesis; judge whether the effect size is large enough to matter in practice "
            "for this research question."
        )
    tail = _objective_clause(project, objective_index)
    text = " ".join(parts)
    return (text + tail).strip()
