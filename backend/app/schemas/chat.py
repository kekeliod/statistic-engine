from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    role: str
    content: str
    meta: dict
    created_at: datetime


class ChatSend(BaseModel):
    dataset_id: int
    message: str


class ChatTurn(BaseModel):
    user: ChatMessageOut
    assistant: ChatMessageOut
    analysis_ids: list[int]
    source: str
