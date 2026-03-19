from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.catalog import ExecutionStatus
from app.runtime.builder import RuntimeManager
from app.schemas import ExecutionSessionResponse, SessionStateResponse, TreeResponse, TreeSummary, TreeUpsertRequest, ValidationResult
from app.storage import (
    create_execution_session,
    delete_tree,
    get_execution_session,
    get_tree,
    list_trees,
    save_tree,
    session_response,
    update_execution_session,
)
from app.validation import validate_tree_payload

router = APIRouter()


def get_db(request: Request) -> Session:
    return request.state.db


def get_runtime_manager(request: Request) -> RuntimeManager:
    return request.app.state.runtime_manager


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/trees", response_model=list[TreeSummary])
def tree_list(request: Request) -> list[TreeSummary]:
    db = get_db(request)
    return list_trees(db)


@router.post("/trees", response_model=TreeResponse, status_code=status.HTTP_201_CREATED)
def tree_create(payload: TreeUpsertRequest, request: Request) -> TreeResponse:
    db = get_db(request)
    return save_tree(db, payload)


@router.get("/trees/{tree_id}", response_model=TreeResponse)
def tree_get(tree_id: str, request: Request) -> TreeResponse:
    db = get_db(request)
    record = get_tree(db, tree_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tree not found.")
    return TreeResponse.model_validate(
        {
            **record.__dict__,
            "node_count": len(record.nodes),
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type,
                    "label": node.label,
                    "parent_id": node.parent_id,
                    "position": {"x": node.position_x, "y": node.position_y},
                    "config": node.config,
                    "order_index": node.order_index,
                }
                for node in sorted(record.nodes, key=lambda item: (item.parent_id or "", item.order_index, item.id))
            ],
            "edges": [
                {
                    "id": f"{node.parent_id}->{node.id}",
                    "source": node.parent_id,
                    "target": node.id,
                }
                for node in sorted(record.nodes, key=lambda item: (item.parent_id or "", item.order_index, item.id))
                if node.parent_id
            ],
        }
    )


@router.put("/trees/{tree_id}", response_model=TreeResponse)
def tree_update(tree_id: str, payload: TreeUpsertRequest, request: Request) -> TreeResponse:
    db = get_db(request)
    try:
        return save_tree(db, payload, tree_id=tree_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/trees/{tree_id}", status_code=status.HTTP_204_NO_CONTENT)
def tree_delete(tree_id: str, request: Request) -> None:
    db = get_db(request)
    try:
        delete_tree(db, tree_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/trees/{tree_id}/validate", response_model=ValidationResult)
def tree_validate(tree_id: str, request: Request) -> ValidationResult:
    tree = tree_get(tree_id, request)
    return validate_tree_payload(TreeUpsertRequest(**tree.model_dump(include={"name", "description", "root_node_id", "nodes", "edges"})))


@router.post("/trees/{tree_id}/run", response_model=ExecutionSessionResponse, status_code=status.HTTP_201_CREATED)
def tree_run(tree_id: str, request: Request) -> ExecutionSessionResponse:
    tree = tree_get(tree_id, request)
    if not tree.is_valid:
        raise HTTPException(status_code=400, detail="Invalid trees cannot be executed.")
    db = get_db(request)
    runtime_manager = get_runtime_manager(request)
    session_record = create_execution_session(db, tree)
    runtime = runtime_manager.start(session_record.id, tree)
    node_statuses, snapshot = runtime.export_state(started=False)
    updated = update_execution_session(
        db,
        session_record,
        status=ExecutionStatus.IDLE,
        tick_count=0,
        node_statuses={key: value.model_dump() for key, value in node_statuses.items()},
        snapshot=snapshot.model_dump(),
    )
    return session_response(updated)


@router.get("/sessions/{session_id}", response_model=ExecutionSessionResponse)
def session_get(session_id: str, request: Request) -> ExecutionSessionResponse:
    db = get_db(request)
    record = get_execution_session(db, session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Execution session not found.")
    return session_response(record)


@router.get("/sessions/{session_id}/state", response_model=SessionStateResponse)
def session_state(session_id: str, request: Request) -> SessionStateResponse:
    session = session_get(session_id, request)
    tree = tree_get(session.tree_id, request)
    return SessionStateResponse(session=session, tree=tree)


@router.post("/sessions/{session_id}/tick", response_model=ExecutionSessionResponse)
def session_tick(session_id: str, request: Request) -> ExecutionSessionResponse:
    db = get_db(request)
    session_record = get_execution_session(db, session_id)
    if session_record is None:
        raise HTTPException(status_code=404, detail="Execution session not found.")
    tree = tree_get(session_record.tree_id, request)
    if not tree.is_valid:
        raise HTTPException(status_code=400, detail="Invalid trees cannot be executed.")

    runtime_manager = get_runtime_manager(request)
    runtime = runtime_manager.get(session_id, tree, session_record.tick_count)
    runtime.behaviour_tree.tick()
    node_statuses, snapshot = runtime.export_state(started=True)
    updated = update_execution_session(
        db,
        session_record,
        status=snapshot.root_status,
        tick_count=session_record.tick_count + 1,
        node_statuses={key: value.model_dump() for key, value in node_statuses.items()},
        snapshot=snapshot.model_dump(),
    )
    return session_response(updated)


@router.post("/sessions/{session_id}/reset", response_model=ExecutionSessionResponse)
def session_reset(session_id: str, request: Request) -> ExecutionSessionResponse:
    db = get_db(request)
    session_record = get_execution_session(db, session_id)
    if session_record is None:
        raise HTTPException(status_code=404, detail="Execution session not found.")
    tree = tree_get(session_record.tree_id, request)
    runtime_manager = get_runtime_manager(request)
    runtime = runtime_manager.reset(session_id, tree)
    node_statuses, snapshot = runtime.export_state(started=False)
    updated = update_execution_session(
        db,
        session_record,
        status=ExecutionStatus.IDLE,
        tick_count=0,
        node_statuses={key: value.model_dump() for key, value in node_statuses.items()},
        snapshot=snapshot.model_dump(),
    )
    return session_response(updated)

