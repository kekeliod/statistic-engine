from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))

    # Which project objective this analysis addresses (0-based index into
    # Project.objectives), or None for ad-hoc analyses.
    objective_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    method: Mapped[str] = mapped_column(String(64))  # registry key, e.g. "independent_ttest"
    # role -> column name(s). A role maps to a str for arity 1, or list[str] for arity n.
    variables: Mapped[dict] = mapped_column(JSON, default=dict)
    params: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|complete|failed
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # serialised StatResult
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    project: Mapped["Project"] = relationship()  # noqa: F821
    charts: Mapped[list["Chart"]] = relationship(  # noqa: F821
        back_populates="analysis", cascade="all, delete-orphan"
    )
