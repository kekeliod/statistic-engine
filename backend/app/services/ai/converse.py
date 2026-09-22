"""Natural-language interaction over a project's dataset.

Returns:
    {
      "reply": str,
      "analyses": [ {method, variables, params, objective_index, outcome} ]   # outcome = run_analysis() dict
      "source": "ai" | "pattern",
    }

The router persists any analyses and swaps the run outcome for the saved row.
"""
from __future__ import annotations

import re

import pandas as pd

from app.core.config import settings
from app.services.ai.client import get_anthropic, model_name
from app.services.ai.tools import analysis_tool
from app.services.stats import run_analysis
from app.services.stats.registry import METHODS
from app.services.type_inference import infer_all_types

_COMPARE_RE = re.compile(r"\b(compar|differ|between|versus|\bvs\b|higher in|lower in)", re.I)
_RELATE_RE = re.compile(r"\b(correlat|relationship|associat|related|predict|linked)", re.I)
_DESCRIBE_RE = re.compile(r"\b(describe|summar|distribution|average|\bmean\b|median|frequency)", re.I)


def _columns_in(text: str, df: pd.DataFrame) -> list[str]:
    t = text.lower()
    return [c for c in df.columns if str(c).lower() in t]


def _pattern_answer(df: pd.DataFrame, query: str) -> dict:
    types = infer_all_types(df)
    cols = _columns_in(query, df)
    numeric = [c for c in cols if types[c].is_numeric_like and types[c].dtype != "binary"]
    groups = [c for c in cols if types[c].dtype in ("binary", "categorical")]

    spec = None
    if _RELATE_RE.search(query) and len(numeric) >= 2:
        spec = ("pearson", {"variable_1": numeric[0], "variable_2": numeric[1]})
    elif _COMPARE_RE.search(query) and numeric and groups:
        n_levels = df[groups[0]].nunique(dropna=True)
        method = "independent_ttest" if n_levels == 2 else "one_way_anova"
        spec = (method, {"outcome": numeric[0], "group": groups[0]})
    elif _DESCRIBE_RE.search(query) and cols:
        spec = ("descriptive", {"variables": cols})

    if not spec:
        return {
            "reply": (
                "Free-form questions need an Anthropic API key to be configured on the "
                "server. Without one I can still run analyses you pick from the method "
                "list, generate objective-based recommendations, and answer simple "
                "phrasings like \"compare <numeric column> between <group column>\" or "
                "\"correlation between <column> and <column>\"."
            ),
            "analyses": [],
            "source": "pattern",
        }

    method, variables = spec
    outcome = run_analysis(df, method, variables, {})
    label = METHODS[method].label
    if outcome["status"] == "complete":
        reply = f"Ran a {label}. {outcome['result']['frequentist']['summary']}"
    else:
        reply = f"I tried a {label} but it could not run: {outcome['error']}"
    return {
        "reply": reply,
        "analyses": [{"method": method, "variables": variables, "params": {},
                      "objective_index": None, "outcome": outcome}],
        "source": "pattern",
    }


def _ai_answer(project, df: pd.DataFrame, history: list[dict], query: str) -> dict:
    client = get_anthropic()
    types = infer_all_types(df)
    col_lines = "\n".join(f"  - {c} [{types[str(c)].dtype}]" for c in df.columns)
    system = (
        "You are a research-statistics assistant embedded in a data-analysis tool. "
        "Answer the user's question about their dataset. When a question calls for a "
        "statistical test, call run_statistical_analysis — a deterministic engine runs "
        "it and returns the numbers; never compute statistics yourself. After the "
        "results come back, explain them in plain language, keeping the frequentist "
        "(p-value) and Bayesian (Bayes factor) statements in separate sentences and "
        "never treating a Bayes factor as 'significance'. Be concise.\n\n"
        f"Project: {project.title}. Aim: {project.research_aim}.\n"
        f"Objectives:\n" + "\n".join(f"{i}. {o}" for i, o in enumerate(project.objectives or []))
        + f"\n\nDataset columns:\n{col_lines}"
    )
    messages = [{"role": m["role"], "content": m["content"]} for m in history[-6:]]
    messages.append({"role": "user", "content": query})

    analyses: list[dict] = []
    for _ in range(settings.ai_max_tool_calls + 1):
        msg = client.messages.create(
            model=model_name(), max_tokens=2000, system=system,
            tools=[analysis_tool()], messages=messages,
        )
        messages.append({"role": "assistant", "content": msg.content})
        tool_uses = [b for b in msg.content if getattr(b, "type", None) == "tool_use"]
        if not tool_uses:
            text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
            return {"reply": text.strip(), "analyses": analyses, "source": "ai"}

        results = []
        for tu in tool_uses:
            inp = tu.input or {}
            outcome = run_analysis(df, inp.get("method", ""), inp.get("variables", {}),
                                   inp.get("params", {}))
            analyses.append({
                "method": inp.get("method"), "variables": inp.get("variables", {}),
                "params": inp.get("params", {}), "objective_index": inp.get("objective_index"),
                "outcome": outcome,
            })
            summary = (outcome["result"]["frequentist"]["summary"]
                       if outcome["status"] == "complete" else f"FAILED: {outcome['error']}")
            bayes = ""
            if outcome["status"] == "complete":
                b = outcome["result"]["bayesian"]
                bayes = (f" Bayes factor BF10={b['bayes_factor_10']:.3g}."
                         if b["available"] and b["bayes_factor_10"] is not None
                         else " (no Bayes factor for this test)")
            results.append({"type": "tool_result", "tool_use_id": tu.id,
                            "content": summary + bayes})
        messages.append({"role": "user", "content": results})

    return {"reply": "Reached the analysis step limit for this question.",
            "analyses": analyses, "source": "ai"}


def answer_query(project, df: pd.DataFrame, history: list[dict], query: str) -> dict:
    if get_anthropic() is not None:
        try:
            return _ai_answer(project, df, history, query)
        except Exception as exc:  # noqa: BLE001
            return {"reply": f"AI request failed ({exc}); try picking a method manually.",
                    "analyses": [], "source": "pattern"}
    return _pattern_answer(df, query)
