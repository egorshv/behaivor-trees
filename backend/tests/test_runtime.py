from __future__ import annotations

from app.catalog import ExecutionStatus
from app.runtime.builder import build_runtime_tree
from app.schemas import TreeUpsertRequest


def test_runtime_progresses_sequence_with_delayed_action(sample_tree_payload: dict) -> None:
    runtime = build_runtime_tree(TreeUpsertRequest(**sample_tree_payload))

    node_statuses, snapshot = runtime.export_state(started=False)
    assert snapshot.root_status == ExecutionStatus.IDLE
    assert node_statuses["root"].status == ExecutionStatus.IDLE

    runtime.behaviour_tree.tick()
    node_statuses, snapshot = runtime.export_state(started=True)
    assert snapshot.root_status == ExecutionStatus.RUNNING
    assert node_statuses["check"].status == ExecutionStatus.SUCCESS
    assert node_statuses["act"].status == ExecutionStatus.RUNNING

    runtime.behaviour_tree.tick()
    node_statuses, snapshot = runtime.export_state(started=True)
    assert snapshot.root_status == ExecutionStatus.SUCCESS
    assert node_statuses["act"].status == ExecutionStatus.SUCCESS


def test_runtime_decorator_can_remap_status(sample_tree_payload: dict) -> None:
    sample_tree_payload["nodes"] = [
        {
            "id": "root",
            "type": "decorator",
            "label": "Remap",
            "parent_id": None,
            "position": {"x": 0, "y": 0},
            "config": {"success_to": "FAILURE", "failure_to": "SUCCESS", "running_to": "RUNNING"},
            "order_index": 0,
        },
        {
            "id": "leaf",
            "type": "success",
            "label": "Success",
            "parent_id": "root",
            "position": {"x": 0, "y": 160},
            "config": {},
            "order_index": 0,
        },
    ]
    sample_tree_payload["edges"] = [{"id": "root-leaf", "source": "root", "target": "leaf"}]
    sample_tree_payload["root_node_id"] = "root"

    runtime = build_runtime_tree(TreeUpsertRequest(**sample_tree_payload))
    runtime.behaviour_tree.tick()
    _, snapshot = runtime.export_state(started=True)

    assert snapshot.root_status == ExecutionStatus.FAILURE

