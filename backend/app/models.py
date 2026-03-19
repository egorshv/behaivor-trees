from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TreeRecord(Base):
    __tablename__ = "trees"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    root_node_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_errors: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    nodes: Mapped[list["NodeRecord"]] = relationship(
        back_populates="tree",
        cascade="all, delete-orphan",
        order_by="NodeRecord.order_index",
    )
    sessions: Mapped[list["ExecutionSessionRecord"]] = relationship(
        back_populates="tree",
        cascade="all, delete-orphan",
    )


class NodeRecord(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tree_id: Mapped[str] = mapped_column(ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    position_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    tree: Mapped[TreeRecord] = relationship(back_populates="nodes")


class ExecutionSessionRecord(Base):
    __tablename__ = "execution_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tree_id: Mapped[str] = mapped_column(ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="idle")
    tick_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_tick_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    node_statuses: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    tree: Mapped[TreeRecord] = relationship(back_populates="sessions")

