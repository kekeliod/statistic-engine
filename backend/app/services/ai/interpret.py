"""Optional AI polish of the deterministic interpretation text."""
from __future__ import annotations

from app.services.ai.client import get_anthropic, model_name

_RULES = (
    "Rewrite the interpretation below so it reads naturally for a researcher, WITHOUT "
    "changing any number, direction, or conclusion. Hard rules: keep the frequentist "
    "(p-value / significance) and Bayesian (Bayes factor) statements in separate "
    "sentences; never call a Bayes factor 'significant'; never call a p-value a "
    "probability that the hypothesis is true; keep the note that statistical "
    "significance is not practical importance; keep any assumption warnings. Return "
    "only the rewritten paragraph, 2-5 sentences."
)


def ai_polish(text: str, result: dict, project, objective_index: int | None) -> str:
    client = get_anthropic()
    if client is None:
        return text
    obj = ""
    objs = list(getattr(project, "objectives", []) or [])
    if isinstance(objective_index, int) and 0 <= objective_index < len(objs):
        obj = f'\nObjective being addressed: "{objs[objective_index]}"'
    try:
        msg = client.messages.create(
            model=model_name(),
            max_tokens=600,
            system=_RULES,
            messages=[{"role": "user", "content": f"{text}{obj}"}],
        )
        out = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()
        return out or text
    except Exception:  # noqa: BLE001
        return text
