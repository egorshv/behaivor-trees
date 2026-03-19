from __future__ import annotations

from collections import defaultdict

from app.catalog import COMPOSITE_NODE_TYPES, DECORATOR_NODE_TYPES, LEAF_NODE_TYPES, SUPPORTED_NODE_TYPES
from app.schemas import TreeUpsertRequest, ValidationIssue, ValidationResult


def validate_tree_payload(payload: TreeUpsertRequest) -> ValidationResult:
    errors: list[ValidationIssue] = []
    nodes_by_id = {}
    children_by_parent: dict[str | None, list[str]] = defaultdict(list)

    for node in payload.nodes:
        if node.id in nodes_by_id:
            errors.append(ValidationIssue(node_id=node.id, message="Duplicate node id."))
            continue
        if node.type not in SUPPORTED_NODE_TYPES:
            errors.append(ValidationIssue(node_id=node.id, message=f"Unsupported node type: {node.type}."))
        nodes_by_id[node.id] = node
        children_by_parent[node.parent_id].append(node.id)

    if not payload.nodes:
        errors.append(ValidationIssue(message="Tree must contain at least one node."))
        return ValidationResult(valid=False, errors=errors, root_node_id=None)

    expected_edges = {(node.parent_id, node.id) for node in payload.nodes if node.parent_id}
    provided_edges = {(edge.source, edge.target) for edge in payload.edges}
    if payload.edges and provided_edges != expected_edges:
        errors.append(ValidationIssue(message="Edges must match each node parent_id relationship."))

    incoming_count: dict[str, int] = defaultdict(int)
    for node in payload.nodes:
        if node.parent_id:
            incoming_count[node.id] += 1
            if node.parent_id not in nodes_by_id:
                errors.append(
                    ValidationIssue(node_id=node.id, message=f"Parent node '{node.parent_id}' does not exist.")
                )

    roots = [node.id for node in payload.nodes if node.parent_id is None]
    if len(roots) != 1:
        errors.append(ValidationIssue(message="Tree must have exactly one root node."))
    root_node_id = roots[0] if len(roots) == 1 else payload.root_node_id

    if payload.root_node_id and roots and payload.root_node_id != roots[0]:
        errors.append(ValidationIssue(message="root_node_id must match the node without a parent."))

    for node in payload.nodes:
        child_count = len(children_by_parent.get(node.id, []))
        if node.type in COMPOSITE_NODE_TYPES and child_count == 0:
            errors.append(ValidationIssue(node_id=node.id, message="Composite nodes must have at least one child."))
        if node.type in DECORATOR_NODE_TYPES and child_count != 1:
            errors.append(ValidationIssue(node_id=node.id, message="Decorator nodes must have exactly one child."))
        if node.type in LEAF_NODE_TYPES and child_count != 0:
            errors.append(ValidationIssue(node_id=node.id, message="Leaf nodes cannot have children."))

    if roots:
        visited: set[str] = set()
        active: set[str] = set()

        def dfs(node_id: str) -> None:
            if node_id in active:
                errors.append(ValidationIssue(node_id=node_id, message="Cycle detected in tree."))
                return
            if node_id in visited:
                return
            active.add(node_id)
            visited.add(node_id)
            for child_id in sorted(
                children_by_parent.get(node_id, []),
                key=lambda candidate: nodes_by_id[candidate].order_index,
            ):
                dfs(child_id)
            active.remove(node_id)

        dfs(roots[0])
        disconnected = set(nodes_by_id) - visited
        for node_id in sorted(disconnected):
            errors.append(ValidationIssue(node_id=node_id, message="Node is disconnected from the root."))

    return ValidationResult(valid=not errors, errors=errors, root_node_id=root_node_id)

