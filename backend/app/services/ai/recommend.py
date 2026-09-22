"""Objective-aware analysis recommendations (AI, with a rule-based fallback)."""
from __future__ import annotations

import json

from app.services.ai.client import get_anthropic, model_name
from app.services.ai.tools import recommendations_tool
from app.services.stats import selection
from app.services.stats.registry import METHODS


def _profile_digest(profile: dict) -> str:
    lines = []
    for c in profile.get("columns", []):
        bits = [f"{c['name']} [{c['dtype']}]", f"{c['non_null_count']} non-null"]
        if c.get("unique_count") is not None:
            bits.append(f"{c['unique_count']} unique")
        if c.get("mean") is not None:
            bits.append(f"mean {c['mean']:.3g}")
        if c.get("top_values"):
            bits.append("values: " + ", ".join(str(t["value"]) for t in c["top_values"]))
        lines.append("  - " + "; ".join(bits))
    return "\n".join(lines)


def _normalise(rec: dict, objectives: list[str]) -> dict | None:
    key = rec.get("method_key")
    if key not in METHODS:
        return None
    oi = rec.get("objective_index")
    return {
        "objective_index": oi,
        "objective_text": objectives[oi] if isinstance(oi, int) and 0 <= oi < len(objectives) else "",
        "method_key": key,
        "method_label": METHODS[key].label,
        "rationale": rec.get("rationale", ""),
        "confidence": rec.get("confidence", "medium"),
        "suggested_variables": rec.get("suggested_variables", {}) or {},
        "chart_suggestion": rec.get("chart_suggestion", ""),
        "alternative_method_key": rec.get("alternative_method_key")
        if rec.get("alternative_method_key") in METHODS else None,
        "source": "ai",
    }


def _ai_recommend(project, profile: dict) -> list[dict]:
    client = get_anthropic()
    objectives = list(project.objectives or [])
    system = (
        "You are a research statistician. Given a study's objectives and a dataset "
        "profile, choose which statistical methods best answer each objective. You do "
        "not compute anything — a separate deterministic engine runs the tests. Only "
        "use method keys from the tool enum. Prefer the simplest method that answers "
        "the question; add a non-parametric alternative where assumptions are likely "
        "to fail. Every analysis will be reported frequentist-and-Bayesian side by "
        "side, so note when a method has no Bayes factor is not your concern here."
    )
    user = (
        f"Project: {project.title}\nAim: {project.research_aim}\n\nObjectives:\n"
        + "\n".join(f"{i}. {o}" for i, o in enumerate(objectives))
        + "\n\nResearch questions:\n"
        + "\n".join(f"- {q}" for q in (project.research_questions or []))
        + "\n\nDataset columns:\n"
        + _profile_digest(profile)
        + "\n\nCall record_recommendations once with 1-3 recommendations per objective."
    )
    msg = client.messages.create(
        model=model_name(),
        max_tokens=4000,
        system=system,
        tools=[recommendations_tool()],
        tool_choice={"type": "tool", "name": "record_recommendations"},
        messages=[{"role": "user", "content": user}],
    )
    payload = None
    for block in msg.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_recommendations":
            payload = block.input
            break
    if not payload:
        raise ValueError("model did not return recommendations")
    recs = [_normalise(r, objectives) for r in payload.get("recommendations", [])]
    recs = [r for r in recs if r]
    if not recs:
        raise ValueError("no valid recommendations after normalisation")
    return recs


def recommend_analyses(project, profile: dict) -> list[dict]:
    """Returns recommendations tagged source='ai' or source='rules'."""
    if get_anthropic() is not None:
        try:
            return _ai_recommend(project, profile)
        except Exception:  # noqa: BLE001 — any AI failure falls back to rules
            pass
    return selection.recommend_analyses(project, profile)
