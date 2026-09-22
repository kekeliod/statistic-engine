"""AI layer: recommendation engine and natural-language interaction.

The LLM never computes a statistic. It only (a) chooses which registered method
fits a research objective and explains why, and (b) explains results in plain
language. All numbers come from app.services.stats.

Everything here degrades gracefully: when no ANTHROPIC_API_KEY is configured,
`recommend_analyses` falls back to the deterministic rule engine
(app.services.stats.selection) and `answer_query` falls back to a small
pattern matcher, so the product is fully usable without a key.
"""

from app.services.ai.client import ai_available
from app.services.ai.recommend import recommend_analyses

__all__ = ["ai_available", "recommend_analyses"]
