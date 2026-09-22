import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.dataset import Dataset
from app.models.project import Project
from app.models.report import Report
from app.routers.analyses import load_dataframe
from app.schemas.report import ReportCreate, ReportOut
from app.services.quality_engine import run_quality_report
from app.services.report import build_report_doc, render_docx, render_html

router = APIRouter(tags=["reports"])


@router.post("/api/projects/{project_id}/reports", response_model=ReportOut, status_code=201)
def create_report(project_id: int, payload: ReportCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    q = select(Analysis).where(Analysis.project_id == project_id)
    if payload.analysis_ids:
        q = q.where(Analysis.id.in_(payload.analysis_ids))
    analyses = list(db.execute(q.order_by(Analysis.created_at)).scalars().all())
    if not analyses:
        raise HTTPException(status_code=409, detail="Run at least one analysis before generating a report.")

    dataset = db.get(Dataset, analyses[0].dataset_id)
    if not dataset:
        raise HTTPException(status_code=410, detail="The dataset for these analyses no longer exists.")

    profile = run_quality_report(load_dataframe(dataset))
    doc = build_report_doc(project, dataset, profile, analyses, title=payload.title)

    out_dir = Path(settings.upload_dir) / str(project_id) / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = uuid.uuid4().hex
    if payload.format == "docx":
        path = out_dir / f"{stem}.docx"
        render_docx(doc, path)
    else:
        path = out_dir / f"{stem}.html"
        path.write_text(render_html(doc), encoding="utf-8")

    report = Report(
        project_id=project_id, title=doc["title"], format=payload.format,
        stored_path=str(path), sections=doc,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/api/projects/{project_id}/reports", response_model=list[ReportOut])
def list_reports(project_id: int, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    return db.execute(
        select(Report).where(Report.project_id == project_id).order_by(Report.created_at.desc())
    ).scalars().all()


@router.get("/api/reports/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    path = Path(report.stored_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Report file is missing on disk.")
    media = ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"
             if report.format == "docx" else "text/html")
    safe = "".join(c for c in report.title if c.isalnum() or c in " -_").strip() or "report"
    return FileResponse(path, media_type=media, filename=f"{safe}.{report.format}")
