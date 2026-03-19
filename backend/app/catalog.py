from __future__ import annotations

from enum import StrEnum


class NodeType(StrEnum):
    SEQUENCE = "sequence"
    SELECTOR = "selector"
    PARALLEL = "parallel"
    INVERTER = "inverter"
    DECORATOR = "decorator"
    ACTION = "action"
    CONDITION = "condition"
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class ExecutionStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    INVALID = "invalid"


COMPOSITE_NODE_TYPES = {
    NodeType.SEQUENCE,
    NodeType.SELECTOR,
    NodeType.PARALLEL,
}
DECORATOR_NODE_TYPES = {
    NodeType.INVERTER,
    NodeType.DECORATOR,
}
LEAF_NODE_TYPES = {
    NodeType.ACTION,
    NodeType.CONDITION,
    NodeType.SUCCESS,
    NodeType.FAILURE,
    NodeType.RUNNING,
}
SUPPORTED_NODE_TYPES = COMPOSITE_NODE_TYPES | DECORATOR_NODE_TYPES | LEAF_NODE_TYPES

