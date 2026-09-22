"""Bridges an Analysis + its dataset to a rendered chart file."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.services.viz.charts import alternate_kinds, chart_for_result, render_chart


def build_chart(analysis, df: pd.DataFrame, kind: str | None = None) -> dict:
    """Render a chart for a completed analysis. Returns a dict ready to persist as Chart."""
    result = analysis.result
    if not result:
        raise ValueError("Analysis has no result to chart.")
    chosen = kind or chart_for_result(result)
    out_dir = Path(settings.upload_dir) / str(analysis.project_id) / "charts"
    path, _name, title = render_chart(chosen, df, result, out_dir)
    return {
        "project_id": analysis.project_id,
        "analysis_id": analysis.id,
        "kind": chosen,
        "title": title,
        "stored_path": str(path),
        "spec": {"method": result.get("method"), "available_kinds": alternate_kinds(result.get("method", ""))},
    }
