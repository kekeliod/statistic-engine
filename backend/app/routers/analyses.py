from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.dataset import Dataset
from app.models.project import Project
from app.schemas.analysis import AnalysisCreate, AnalysisOut, MethodSpecOut, RecommendationOut
from app.models.chart import Chart
from app.services import dataset_service
from app.services.ai import recommend_analyses
from app.services.ai.client import ai_available
from app.services.ai.interpret import ai_polish
from app.services.chart_service import build_chart
from app.services.interpretation import template_interpretation
from app.services.quality_engine import run_quality_report
from app.services.stats import run_analysis
from app.services.stats.registry import METHODS

router = APIRouter(tags=["analyses"])


@router.get("/api/methods", response_model=list[MethodSpecOut])
def list_methods():
    return [
        MethodSpecOut(
            key=s.key, label=s.label, category=s.category, description=s.description,
            when_to_use=s.when_to_use, param_defaults=s.param_defaults,
            bayesian_supported=s.bayesian_supported,
            roles=[
                {"name": r.name, "arity": r.arity, "dtypes": list(r.dtypes),
                 "description": r.description}
                for r in s.roles
            ],
        )
        for s in METHODS.values()
    ]


def load_dataframe(dataset: Dataset):
    path = Path(dataset.stored_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Stored dataset file is missing on disk.")
    return dataset_service.read_dataframe(path, dataset.file_type, dataset.sheet_name)


_load_dataframe = load_dataframe  # backwards-compatible alias


def _generate_default_chart(db: Session, analysis: Analysis, df) -> None:
    """Best-effort default chart. A rendering failure must not fail the analysis."""
    if analysis.status != "complete" or not analysis.result:
        return
    try:
        chart_data = build_chart(analysis, df)  # renders the PNG; may raise
    except Exception:  # noqa: BLE001
        return
    db.add(Chart(**chart_data))
    db.flush()


def _run_and_fill(analysis: Analysis, project: Project, dataset: Dataset):
    """Runs the analysis, fills status/result/interpretation, returns the loaded DataFrame."""
    df = load_dataframe(dataset)
    outcome = run_analysis(df, analysis.method, analysis.variables, analysis.params)
    analysis.status = outcome["status"]
    analysis.result = outcome["result"]
    analysis.error = outcome["error"]
    if outcome["status"] == "complete":
        analysis.interpretation = template_interpretation(
            outcome["result"], project, analysis.objective_index,
            alpha=float({**analysis.params}.get("alpha", 0.05)),
        )
    else:
        analysis.interpretation = None
    return df


@router.post("/api/projects/{project_id}/analyses", response_model=AnalysisOut, status_code=201)
def create_analysis(project_id: int, payload: AnalysisCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    dataset = db.get(Dataset, payload.dataset_id)
    if not dataset or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found for this project.")
    if payload.method not in METHODS:
        raise HTTPException(status_code=400, detail=f"Unknown method '{payload.method}'.")

    analysis = Analysis(
        project_id=project_id,
        dataset_id=dataset.id,
        objective_index=payload.objective_index,
        method=payload.method,
        variables=payload.variables,
        params=payload.params,
        status="pending",
    )
    df = _run_and_fill(analysis, project, dataset)
    db.add(analysis)
    db.flush()
    _generate_default_chart(db, analysis, df)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get("/api/projects/{project_id}/analyses", response_model=list[AnalysisOut])
def list_analyses(project_id: int, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    return db.execute(
        select(Analysis).where(Analysis.project_id == project_id).order_by(Analysis.created_at.desc())
    ).scalars().all()


@router.get("/api/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return analysis


@router.post("/api/analyses/{analysis_id}/rerun", response_model=AnalysisOut)
def rerun_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    project = db.get(Project, analysis.project_id)
    dataset = db.get(Dataset, analysis.dataset_id)
    if not dataset:
        raise HTTPException(status_code=410, detail="The dataset for this analysis no longer exists.")
    df = _run_and_fill(analysis, project, dataset)
    for old in list(analysis.charts):
        db.delete(old)
    db.flush()
    _generate_default_chart(db, analysis, df)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.delete("/api/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    db.delete(analysis)
    db.commit()


@router.post("/api/projects/{project_id}/recommendations", response_model=list[RecommendationOut])
def recommend(project_id: int, dataset_id: int | None = None, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    dataset = (
        db.get(Dataset, dataset_id)
        if dataset_id
        else db.execute(
            select(Dataset).where(Dataset.project_id == project_id, Dataset.is_active == True)  # noqa: E712
        ).scalars().first()
    )
    if not dataset or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Upload a dataset before requesting recommendations.")
    profile = run_quality_report(load_dataframe(dataset))
    return recommend_analyses(project, profile)


@router.post("/api/analyses/{analysis_id}/interpret", response_model=AnalysisOut)
def interpret_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if analysis.status != "complete" or not analysis.result:
        raise HTTPException(status_code=409, detail="This analysis has no completed result to interpret.")
    project = db.get(Project, analysis.project_id)
    alpha = float({**analysis.params}.get("alpha", 0.05))
    base = template_interpretation(analysis.result, project, analysis.objective_index, alpha=alpha)
    analysis.interpretation = ai_polish(base, analysis.result, project, analysis.objective_index) \
        if ai_available() else base
    db.commit()
    db.refresh(analysis)
    return analysis
