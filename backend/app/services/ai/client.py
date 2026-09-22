"""Anthropic client factory. Returns None when no key is configured."""
from __future__ import annotations

import functools

from app.core.config import settings


def ai_available() -> bool:
    return settings.ai_available


@functools.lru_cache(maxsize=1)
def get_anthropic():
    """The Anthropic client, or None if no API key is set.

    Cached so we don't rebuild it per request. Import is local so the package
    imports cleanly even if `anthropic` is somehow missing.
    """
    if not settings.ai_available:
        return None
    try:
        import anthropic
    except ImportError:  # pragma: no cover
        return None
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def model_name() -> str:
    return settings.anthropic_model
