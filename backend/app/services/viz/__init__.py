"""Server-rendered charts (matplotlib, PNG). No LLM involved."""

from app.services.viz.charts import chart_for_result, render_chart

__all__ = ["chart_for_result", "render_chart"]
