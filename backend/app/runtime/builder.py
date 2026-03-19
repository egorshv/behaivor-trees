from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

import py_trees

from app.catalog import ExecutionStatus, NodeType
from app.runtime.stubs import StatusMappingDecorator, default_leaf
from app.schemas import NodeExecutionState, SessionSnapshot, TreeResponse, TreeUpsertRequest
from app.validation import validate_tree_payload


def map_runtime_status(status: py_trees.common.Status | None, *, started: bool) -> ExecutionStatus:
    if status is None:
        return ExecutionStatus.IDLE
    if status == py_trees.common.Status.SUCCESS:
        return ExecutionStatus.SUCCESS
    if status == py_trees.common.Status.FAILURE:
        return ExecutionStatus.FAILURE
    if status == py_trees.common.Status.RUNNING:
        return ExecutionStatus.RUNNING
    return ExecutionStatus.INVALID if started else ExecutionStatus.IDLE


@dataclass
class CompiledTree:
    behaviour_tree: py_trees.trees.BehaviourTree
    behaviour_index: dict[str, py_trees.behaviour.Behaviour]
    root_node_id: str

    def export_state(self, *, started: bool) -> tuple[dict[str, NodeExecutionState], SessionSnapshot]:
        node_statuses = {
            node_id: NodeExecutionState(
                status=map_runtime_status(behaviour.status, started=started),
                feedback=behaviour.feedback_message or "",
            )
            for node_id, behaviour in self.behaviour_index.items()
        }
        active_node_ids = [
            node_id
            for node_id, behaviour in self.behaviour_index.items()
            if behaviour.status == py_trees.common.Status.RUNNING
        ]
        root_status = map_runtime_status(self.behaviour_tree.root.status, started=started)
        snapshot = SessionSnapshot(
            root_status=root_status,
            root_node_id=self.root_node_id,
            active_node_ids=active_node_ids,
        )
        return node_statuses, snapshot


def build_runtime_tree(tree: TreeResponse | TreeUpsertRequest) -> CompiledTree:
    if isinstance(tree, TreeUpsertRequest):
        validation = validate_tree_payload(tree)
        if not validation.valid:
            raise ValueError("Cannot build runtime for invalid tree.")
        now = datetime.now(timezone.utc)
        payload = TreeResponse(
            id="transient",
            name=tree.name,
            description=tree.description,
            root_node_id=validation.root_node_id,
            is_valid=True,
            validation_errors=[],
            created_at=now,
            updated_at=now,
            node_count=len(tree.nodes),
            nodes=tree.nodes,
            edges=tree.edges,
        )
    else:
        payload = tree
        if not payload.is_valid:
            raise ValueError("Cannot build runtime for invalid tree.")

    nodes_by_id = {node.id: node for node in payload.nodes}
    children_by_parent: dict[str | None, list] = defaultdict(list)
    for node in payload.nodes:
        children_by_parent[node.parent_id].append(node)
    for child_list in children_by_parent.values():
        child_list.sort(key=lambda item: item.order_index)

    behaviour_index: dict[str, py_trees.behaviour.Behaviour] = {}

    def create_behaviour(node_id: str) -> py_trees.behaviour.Behaviour:
        node = nodes_by_id[node_id]
        child_behaviours = [create_behaviour(child.id) for child in children_by_parent.get(node.id, [])]

        if node.type == NodeType.SEQUENCE:
            behaviour = py_trees.composites.Sequence(
                name=node.label,
                memory=bool(node.config.get("memory", True)),
            )
            for child in child_behaviours:
                behaviour.add_child(child)
        elif node.type == NodeType.SELECTOR:
            behaviour = py_trees.composites.Selector(
                name=node.label,
                memory=bool(node.config.get("memory", False)),
            )
            for child in child_behaviours:
                behaviour.add_child(child)
        elif node.type == NodeType.PARALLEL:
            policy_name = str(node.config.get("policy", "success_on_all"))
            synchronise = bool(node.config.get("synchronise", False))
            if policy_name == "success_on_one":
                policy = py_trees.common.ParallelPolicy.SuccessOnOne()
            else:
                policy = py_trees.common.ParallelPolicy.SuccessOnAll(synchronise=synchronise)
            behaviour = py_trees.composites.Parallel(name=node.label, policy=policy)
            for child in child_behaviours:
                behaviour.add_child(child)
        elif node.type == NodeType.INVERTER:
            behaviour = py_trees.decorators.Inverter(name=node.label, child=child_behaviours[0])
        elif node.type == NodeType.DECORATOR:
            mapping = {
                "success": str(node.config.get("success_to", "SUCCESS")),
                "failure": str(node.config.get("failure_to", "FAILURE")),
                "running": str(node.config.get("running_to", "RUNNING")),
            }
            behaviour = StatusMappingDecorator(name=node.label, child=child_behaviours[0], mapping=mapping)
        else:
            behaviour = default_leaf(node.type.value, node.label, node.config)

        setattr(behaviour, "bt_node_id", node.id)
        behaviour_index[node.id] = behaviour
        return behaviour

    root_node_id = payload.root_node_id or next(node.id for node in payload.nodes if node.parent_id is None)
    root = create_behaviour(root_node_id)
    return CompiledTree(
        behaviour_tree=py_trees.trees.BehaviourTree(root=root),
        behaviour_index=behaviour_index,
        root_node_id=root_node_id,
    )


class RuntimeManager:
    def __init__(self) -> None:
        self._runtimes: dict[str, CompiledTree] = {}

    def start(self, session_id: str, tree: TreeResponse) -> CompiledTree:
        runtime = build_runtime_tree(tree)
        self._runtimes[session_id] = runtime
        return runtime

    def reset(self, session_id: str, tree: TreeResponse) -> CompiledTree:
        return self.start(session_id, tree)

    def get(self, session_id: str, tree: TreeResponse, tick_count: int) -> CompiledTree:
        runtime = self._runtimes.get(session_id)
        if runtime is None:
            runtime = build_runtime_tree(tree)
            for _ in range(tick_count):
                runtime.behaviour_tree.tick()
            self._runtimes[session_id] = runtime
        return runtime

    def forget(self, session_id: str) -> None:
        self._runtimes.pop(session_id, None)
