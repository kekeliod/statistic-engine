from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.chart import Chart
from app.models.dataset import Dataset
from app.routers.analyses import load_dataframe
from app.schemas.chart import ChartCreate, ChartOut
from app.services.chart_service import build_chart

router = APIRouter(tags=["charts"])


def generate_default_chart(db: Session, analysis: Analysis, df) -> Chart | None:
    """Best-effort: a failed chart must never fail the analysis."""
    if analysis.status != "complete" or not analysis.result:
        return None
    try:
        chart = Chart(**build_chart(analysis, df))
    except Exception:  # noqa: BLE001
        return None
    db.add(chart)
    db.flush()
    return chart


@router.get("/api/analyses/{analysis_id}/charts", response_model=list[ChartOut])
def list_charts(analysis_id: int, db: Session = Depends(get_db)):
    if not db.get(Analysis, analysis_id):
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return db.execute(
        select(Chart).where(Chart.analysis_id == analysis_id).order_by(Chart.created_at)
    ).scalars().all()


@router.post("/api/analyses/{analysis_id}/charts", response_model=ChartOut, status_code=201)
def create_chart(analysis_id: int, payload: ChartCreate, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if analysis.status != "complete" or not analysis.result:
        raise HTTPException(status_code=409, detail="Analysis has no completed result to chart.")
    dataset = db.get(Dataset, analysis.dataset_id)
    if not dataset:
        raise HTTPException(status_code=410, detail="The dataset for this analysis no longer exists.")
    try:
        chart = Chart(**build_chart(analysis, load_dataframe(dataset), payload.kind))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.add(chart)
    db.commit()
    db.refresh(chart)
    return chart


@router.get("/api/charts/{chart_id}")
def get_chart_image(chart_id: int, db: Session = Depends(get_db)):
    chart = db.get(Chart, chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found.")
    path = Path(chart.stored_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Chart image is missing on disk.")
    return FileResponse(path, media_type="image/png")
