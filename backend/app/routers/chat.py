from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.chat import ChatMessage
from app.models.dataset import Dataset
from app.models.project import Project
from app.schemas.chat import ChatMessageOut, ChatSend, ChatTurn
from app.routers.analyses import _generate_default_chart, load_dataframe
from app.services.ai.converse import answer_query
from app.services.interpretation import template_interpretation

router = APIRouter(tags=["chat"])


@router.get("/api/projects/{project_id}/chat", response_model=list[ChatMessageOut])
def get_chat(project_id: int, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    return db.execute(
        select(ChatMessage).where(ChatMessage.project_id == project_id).order_by(ChatMessage.created_at)
    ).scalars().all()


@router.post("/api/projects/{project_id}/chat", response_model=ChatTurn)
def send_chat(project_id: int, payload: ChatSend, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    dataset = db.get(Dataset, payload.dataset_id)
    if not dataset or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found for this project.")

    history = [
        {"role": m.role, "content": m.content}
        for m in db.execute(
            select(ChatMessage).where(ChatMessage.project_id == project_id).order_by(ChatMessage.created_at)
        ).scalars().all()
    ]
    df = load_dataframe(dataset)
    result = answer_query(project, df, history, payload.message)

    analysis_ids: list[int] = []
    for spec in result["analyses"]:
        outcome = spec["outcome"]
        analysis = Analysis(
            project_id=project_id, dataset_id=dataset.id,
            objective_index=spec.get("objective_index"),
            method=spec["method"] or "", variables=spec["variables"], params=spec.get("params", {}),
            status=outcome["status"], result=outcome["result"], error=outcome["error"],
            interpretation=(
                template_interpretation(outcome["result"], project, spec.get("objective_index"))
                if outcome["status"] == "complete" else None
            ),
        )
        db.add(analysis)
        db.flush()
        _generate_default_chart(db, analysis, df)
        analysis_ids.append(analysis.id)

    user_msg = ChatMessage(project_id=project_id, role="user", content=payload.message, meta={})
    assistant_msg = ChatMessage(
        project_id=project_id, role="assistant", content=result["reply"],
        meta={"analysis_ids": analysis_ids, "source": result["source"]},
    )
    db.add_all([user_msg, assistant_msg])
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    return ChatTurn(user=user_msg, assistant=assistant_msg, analysis_ids=analysis_ids,
                    source=result["source"])
