from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.dataset import Dataset
from app.models.project import Project
from app.schemas.dataset import DatasetOut, DatasetPreview
from app.schemas.quality import DataQualityReport
from app.services import dataset_service, quality_engine

router = APIRouter(tags=["datasets"])


@router.post("/api/projects/{project_id}/datasets", response_model=DatasetOut, status_code=201)
def upload_dataset(
    project_id: int,
    file: UploadFile,
    sheet_name: str | None = Form(None),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    stored_path, file_type, original_filename = dataset_service.save_upload(project_id, file)

    try:
        sheets = dataset_service.list_sheets(stored_path, file_type)
        if len(sheets) > 1 and not sheet_name:
            raise HTTPException(
                status_code=422,
                detail={"requires_sheet_selection": True, "sheets": sheets},
            )
        if sheet_name and sheets and sheet_name not in sheets:
            raise HTTPException(status_code=400, detail=f"Sheet '{sheet_name}' not found in workbook.")

        effective_sheet = sheet_name or (sheets[0] if sheets else None)
        n_rows, n_columns, columns = dataset_service.extract_metadata(
            stored_path, file_type, effective_sheet
        )
    except HTTPException:
        stored_path.unlink(missing_ok=True)
        raise

    next_version = (
        db.execute(
            select(func.coalesce(func.max(Dataset.version), 0)).where(Dataset.project_id == project_id)
        ).scalar_one()
        + 1
    )
    db.execute(
        Dataset.__table__.update().where(Dataset.project_id == project_id).values(is_active=False)
    )

    dataset = Dataset(
        project_id=project_id,
        original_filename=original_filename,
        stored_path=str(stored_path),
        file_type=file_type,
        sheet_name=effective_sheet,
        n_rows=n_rows,
        n_columns=n_columns,
        columns=columns,
        version=next_version,
        is_active=True,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("/api/projects/{project_id}/datasets", response_model=list[DatasetOut])
def list_datasets(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return db.execute(
        select(Dataset).where(Dataset.project_id == project_id).order_by(Dataset.version.desc())
    ).scalars().all()


@router.get("/api/datasets/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


@router.get("/api/datasets/{dataset_id}/preview", response_model=DatasetPreview)
def preview_dataset(
    dataset_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    path = Path(dataset.stored_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Stored dataset file is missing on disk.")

    rows, total = dataset_service.get_preview(
        path, dataset.file_type, offset, limit, dataset.sheet_name
    )
    return DatasetPreview(columns=dataset.columns, rows=rows, total_rows=total, offset=offset, limit=limit)


@router.get("/api/datasets/{dataset_id}/quality", response_model=DataQualityReport)
def get_data_quality(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    path = Path(dataset.stored_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Stored dataset file is missing on disk.")

    df = dataset_service.read_dataframe(path, dataset.file_type, dataset.sheet_name)
    return quality_engine.run_quality_report(df)


@router.delete("/api/datasets/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    Path(dataset.stored_path).unlink(missing_ok=True)
    db.delete(dataset)
    db.commit()
