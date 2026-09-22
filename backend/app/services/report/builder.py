"""Assemble a structured report document from a project's stored analyses.

Pure data assembly — no rendering, no LLM. `build_report_doc` returns a dict that
the HTML and DOCX renderers both consume.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.analysis import Analysis
from app.models.dataset import Dataset
from app.models.project import Project
from app.services.stats.registry import METHODS


def _dataset_section(dataset: Dataset, profile: dict) -> dict:
    return {
        "filename": dataset.original_filename,
        "sheet_name": dataset.sheet_name,
        "n_rows": dataset.n_rows,
        "n_columns": dataset.n_columns,
        "columns": [
            {"name": c["name"], "dtype": c["dtype"],
             "missing_pct": c["missing_pct"], "unique_count": c["unique_count"]}
            for c in profile.get("columns", [])
        ],
    }


def _quality_section(profile: dict) -> dict:
    score = profile.get("score", {})
    dups = profile.get("duplicates", {})
    return {
        "score": score,
        "duplicate_row_count": dups.get("duplicate_row_count", 0),
        "outlier_columns": [o["column"] for o in profile.get("outliers", [])],
        "invalid_values": profile.get("invalid_values", []),
    }


def _analysis_section(a: Analysis, project: Project) -> dict:
    r = a.result or {}
    f = r.get("frequentist", {})
    b = r.get("bayesian", {})
    obj = None
    if a.objective_index is not None and 0 <= a.objective_index < len(project.objectives or []):
        obj = project.objectives[a.objective_index]
    return {
        "id": a.id,
        "method": a.method,
        "method_label": r.get("method_label", a.method),
        "objective": obj,
        "objective_index": a.objective_index,
        "variables": a.variables,
        "status": a.status,
        "error": a.error,
        "n_used": r.get("n_used"),
        "n_excluded": r.get("n_excluded"),
        "frequentist": f,
        "bayesian": b,
        "assumptions": r.get("assumptions", []),
        "tables": r.get("tables", []),
        "interpretation": a.interpretation,
        "chart": ({"id": a.charts[0].id, "title": a.charts[0].title,
                   "stored_path": a.charts[0].stored_path} if a.charts else None),
    }


def _limitations(analyses: list[dict], quality: dict) -> list[str]:
    out: list[str] = []
    q = quality.get("score", {})
    total_excluded = sum(a.get("n_excluded") or 0 for a in analyses if a["status"] == "complete")
    if total_excluded > 0 or q.get("completeness", 100) < 98:
        out.append(
            f"The dataset is {q.get('completeness', 100)}% complete; across the analyses, "
            f"{total_excluded} row(s) with missing values in the analysis variables were "
            "excluded listwise, which can bias estimates if the data are not missing at random."
        )
    if quality.get("duplicate_row_count", 0) > 0:
        out.append(
            f"{quality['duplicate_row_count']} duplicate row(s) were detected and left in place; "
            "confirm whether these are genuine repeated observations."
        )
    small = sorted({a["method_label"] for a in analyses
                    if a["status"] == "complete" and (a.get("n_used") or 0) < 20})
    if small:
        out.append(
            "Small samples (n < 20) limit statistical power for: " + ", ".join(small)
            + ". Treat non-significant results as inconclusive rather than as evidence of no effect."
        )
    no_bayes = sorted({a["method_label"] for a in analyses
                       if a["status"] == "complete" and not a["bayesian"].get("available")})
    if no_bayes:
        out.append(
            "A Bayes factor is not available from the current toolset for: "
            + ", ".join(no_bayes)
            + "; only the frequentist result is reported for these. Full posterior-based "
            "Bayesian versions would require additional modelling (PyMC)."
        )
    failed_assumptions = []
    for a in analyses:
        for chk in a.get("assumptions", []):
            if chk.get("passed") is False:
                failed_assumptions.append(f"{a['method_label']}: {chk['label']}")
    for item in sorted(set(failed_assumptions)):
        out.append(f"Assumption not met — {item}. See the analysis notes for the suggested alternative.")
    return out


def _recommendations(analyses: list[dict], project: Project) -> list[str]:
    out: list[str] = []
    for a in analyses:
        if a["status"] != "complete":
            continue
        p = a["frequentist"].get("p_value")
        if p is not None and p < 0.05:
            es = a["frequentist"].get("effect_size") or {}
            mag = f" ({es['magnitude']} effect)" if es.get("magnitude") else ""
            label = a["objective"] or a["method_label"]
            out.append(
                f"{a['method_label']} found a statistically significant result for "
                f"\"{label}\"{mag}; interpret alongside the effect size for practical importance."
            )
    if not out:
        out.append(
            "No statistically significant effects were detected in the analyses run so far; "
            "consider whether the sample size is adequate and whether additional variables or "
            "sampling rounds are needed."
        )
    out.append(
        "Report both the frequentist result and, where available, the Bayes factor, and keep "
        "their interpretations distinct in any write-up."
    )
    return out


def build_report_doc(
    project: Project, dataset: Dataset, profile: dict, analyses: list[Analysis], *, title: str | None = None,
) -> dict:
    analysis_sections = [_analysis_section(a, project) for a in analyses]
    quality = _quality_section(profile)
    method_keys = []
    for a in analyses:
        if a.method not in method_keys:
            method_keys.append(a.method)
    methods = [
        {"label": METHODS[k].label, "description": METHODS[k].description,
         "bayesian_supported": METHODS[k].bayesian_supported}
        for k in method_keys if k in METHODS
    ]
    return {
        "title": title or f"{project.title} — Statistical Analysis Report",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "project": {
            "title": project.title,
            "aim": project.research_aim,
            "objectives": list(project.objectives or []),
            "research_questions": list(project.research_questions or []),
            "hypotheses": list(project.hypotheses or []),
        },
        "dataset": _dataset_section(dataset, profile),
        "data_quality": quality,
        "methods": methods,
        "analyses": analysis_sections,
        "limitations": _limitations(analysis_sections, quality),
        "recommendations": _recommendations(analysis_sections, project),
    }
