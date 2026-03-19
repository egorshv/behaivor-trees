from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.catalog import ExecutionStatus, NodeType


class Position(BaseModel):
    x: float = 0
    y: float = 0


class EdgeDTO(BaseModel):
    id: str
    source: str
    target: str


class NodeDTO(BaseModel):
    id: str
    type: NodeType
    label: str
    parent_id: str | None = None
    position: Position = Field(default_factory=Position)
    config: dict[str, Any] = Field(default_factory=dict)
    order_index: int = 0

    @field_validator("config", mode="before")
    @classmethod
    def default_config(cls, value: Any) -> dict[str, Any]:
        return value or {}


class ValidationIssue(BaseModel):
    node_id: str | None = None
    message: str


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    root_node_id: str | None = None


class TreeUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    root_node_id: str | None = None
    nodes: list[NodeDTO] = Field(default_factory=list)
    edges: list[EdgeDTO] = Field(default_factory=list)


class TreeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    root_node_id: str | None
    is_valid: bool
    validation_errors: list[ValidationIssue] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    node_count: int


class TreeResponse(TreeSummary):
    nodes: list[NodeDTO] = Field(default_factory=list)
    edges: list[EdgeDTO] = Field(default_factory=list)


class NodeExecutionState(BaseModel):
    status: ExecutionStatus
    feedback: str = ""


class SessionSnapshot(BaseModel):
    root_status: ExecutionStatus
    root_node_id: str | None = None
    active_node_ids: list[str] = Field(default_factory=list)


class ExecutionSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tree_id: str
    status: ExecutionStatus
    tick_count: int
    last_tick_at: datetime | None
    node_statuses: dict[str, NodeExecutionState] = Field(default_factory=dict)
    snapshot: SessionSnapshot
    created_at: datetime
    updated_at: datetime


class SessionStateResponse(BaseModel):
    session: ExecutionSessionResponse
    tree: TreeResponse

