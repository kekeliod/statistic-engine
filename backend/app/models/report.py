from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    format: Mapped[str] = mapped_column(String(8))  # html | docx
    stored_path: Mapped[str] = mapped_column(String(1000))
    sections: Mapped[dict] = mapped_column(JSON, default=dict)  # the doc snapshot
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
