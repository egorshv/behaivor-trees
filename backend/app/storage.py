from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import ExecutionStatus, NodeType
from app.models import ExecutionSessionRecord, NodeRecord, TreeRecord
from app.schemas import EdgeDTO, ExecutionSessionResponse, NodeDTO, SessionSnapshot, TreeResponse, TreeSummary, TreeUpsertRequest
from app.validation import validate_tree_payload


def _build_edges(nodes: list[NodeDTO]) -> list[EdgeDTO]:
    return [
        EdgeDTO(id=f"{node.parent_id}->{node.id}", source=node.parent_id, target=node.id)
        for node in sorted(nodes, key=lambda item: (item.parent_id or "", item.order_index, item.id))
        if node.parent_id
    ]


def _tree_nodes(records: list[NodeRecord]) -> list[NodeDTO]:
    nodes = [
        NodeDTO(
            id=record.id,
            type=NodeType(record.type),
            label=record.label,
            parent_id=record.parent_id,
            position={"x": record.position_x, "y": record.position_y},
            config=record.config or {},
            order_index=record.order_index,
        )
        for record in sorted(records, key=lambda item: (item.parent_id or "", item.order_index, item.id))
    ]
    return nodes


def _tree_response(record: TreeRecord) -> TreeResponse:
    nodes = _tree_nodes(record.nodes)
    return TreeResponse(
        id=record.id,
        name=record.name,
        description=record.description,
        root_node_id=record.root_node_id,
        is_valid=record.is_valid,
        validation_errors=record.validation_errors,
        created_at=record.created_at,
        updated_at=record.updated_at,
        node_count=len(nodes),
        nodes=nodes,
        edges=_build_edges(nodes),
    )


def _tree_summary(record: TreeRecord) -> TreeSummary:
    return TreeSummary(
        id=record.id,
        name=record.name,
        description=record.description,
        root_node_id=record.root_node_id,
        is_valid=record.is_valid,
        validation_errors=record.validation_errors,
        created_at=record.created_at,
        updated_at=record.updated_at,
        node_count=len(record.nodes),
    )


def list_trees(db: Session) -> list[TreeSummary]:
    query = select(TreeRecord).order_by(TreeRecord.updated_at.desc())
    return [_tree_summary(record) for record in db.scalars(query).unique().all()]


def get_tree(db: Session, tree_id: str) -> TreeRecord | None:
    return db.get(TreeRecord, tree_id)


def save_tree(db: Session, payload: TreeUpsertRequest, tree_id: str | None = None) -> TreeResponse:
    validation = validate_tree_payload(payload)
    record = db.get(TreeRecord, tree_id) if tree_id else TreeRecord()
    if record is None:
        raise LookupError(f"Tree '{tree_id}' was not found.")

    record.name = payload.name
    record.description = payload.description
    record.root_node_id = validation.root_node_id
    record.is_valid = validation.valid
    record.validation_errors = [issue.model_dump() for issue in validation.errors]

    if tree_id is None:
        db.add(record)
        db.flush()

    for existing in list(record.nodes):
        db.delete(existing)
    db.flush()

    for node in payload.nodes:
        db.add(
            NodeRecord(
                id=node.id,
                tree_id=record.id,
                type=node.type.value,
                label=node.label,
                parent_id=node.parent_id,
                position_x=node.position.x,
                position_y=node.position.y,
                config=node.config,
                order_index=node.order_index,
            )
        )
    db.commit()
    db.refresh(record)
    return _tree_response(record)


def delete_tree(db: Session, tree_id: str) -> None:
    record = db.get(TreeRecord, tree_id)
    if record is None:
        raise LookupError(f"Tree '{tree_id}' was not found.")
    db.delete(record)
    db.commit()


def create_execution_session(db: Session, tree: TreeResponse) -> ExecutionSessionRecord:
    record = ExecutionSessionRecord(
        tree_id=tree.id,
        status=ExecutionStatus.IDLE.value,
        tick_count=0,
        last_tick_at=None,
        node_statuses={
            node.id: {"status": ExecutionStatus.IDLE.value, "feedback": ""}
            for node in tree.nodes
        },
        snapshot={
            "root_status": ExecutionStatus.IDLE.value,
            "root_node_id": tree.root_node_id,
            "active_node_ids": [],
        },
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_execution_session(db: Session, session_id: str) -> ExecutionSessionRecord | None:
    return db.get(ExecutionSessionRecord, session_id)


def update_execution_session(
    db: Session,
    session_record: ExecutionSessionRecord,
    *,
    status: ExecutionStatus,
    tick_count: int,
    node_statuses: dict,
    snapshot: dict,
) -> ExecutionSessionRecord:
    session_record.status = status.value
    session_record.tick_count = tick_count
    session_record.node_statuses = node_statuses
    session_record.snapshot = snapshot
    session_record.last_tick_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session_record)
    return session_record


def session_response(record: ExecutionSessionRecord) -> ExecutionSessionResponse:
    return ExecutionSessionResponse(
        id=record.id,
        tree_id=record.tree_id,
        status=record.status,
        tick_count=record.tick_count,
        last_tick_at=record.last_tick_at,
        node_statuses=record.node_statuses,
        snapshot=SessionSnapshot.model_validate(record.snapshot),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def ensure_demo_tree(db: Session) -> None:
    query = select(TreeRecord.id).limit(1)
    if db.execute(query).first():
        return
    payload = TreeUpsertRequest(
        name="Demo Tree",
        description="Seeded sequence tree with a condition and action.",
        root_node_id="root-sequence",
        nodes=[
            NodeDTO(
                id="root-sequence",
                type=NodeType.SEQUENCE,
                label="Root Sequence",
                position={"x": 300, "y": 40},
                config={"memory": True},
                order_index=0,
            ),
            NodeDTO(
                id="guard-condition",
                type=NodeType.CONDITION,
                label="Ready?",
                parent_id="root-sequence",
                position={"x": 150, "y": 220},
                config={"result": "SUCCESS", "delay_ticks": 0},
                order_index=0,
            ),
            NodeDTO(
                id="perform-action",
                type=NodeType.ACTION,
                label="Do Work",
                parent_id="root-sequence",
                position={"x": 450, "y": 220},
                config={"result": "SUCCESS", "delay_ticks": 1},
                order_index=1,
            ),
        ],
        edges=[
            EdgeDTO(id="edge-root-guard", source="root-sequence", target="guard-condition"),
            EdgeDTO(id="edge-root-action", source="root-sequence", target="perform-action"),
        ],
    )
    save_tree(db, payload)

