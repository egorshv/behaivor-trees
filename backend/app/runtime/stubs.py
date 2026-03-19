from __future__ import annotations

from typing import Any

import py_trees


def parse_status(name: str) -> py_trees.common.Status:
    normalized = name.strip().upper()
    return py_trees.common.Status[normalized]


class TimedStatusLeaf(py_trees.behaviour.Behaviour):
    def __init__(self, name: str, result: py_trees.common.Status, delay_ticks: int = 0):
        super().__init__(name=name)
        self.result = result
        self.delay_ticks = max(delay_ticks, 0)
        self.current_tick = 0

    def initialise(self) -> None:
        self.current_tick = 0

    def update(self) -> py_trees.common.Status:
        if self.current_tick < self.delay_ticks:
            self.current_tick += 1
            self.feedback_message = f"Waiting ({self.current_tick}/{self.delay_ticks})"
            return py_trees.common.Status.RUNNING
        self.feedback_message = f"Completed with {self.result.value}"
        return self.result


class StatusMappingDecorator(py_trees.decorators.Decorator):
    def __init__(self, name: str, child: py_trees.behaviour.Behaviour, mapping: dict[str, str] | None = None):
        super().__init__(name=name, child=child)
        self.mapping = {
            "SUCCESS": "SUCCESS",
            "FAILURE": "FAILURE",
            "RUNNING": "RUNNING",
            **{(key or "").upper(): (value or "").upper() for key, value in (mapping or {}).items()},
        }

    def update(self) -> py_trees.common.Status:
        mapped = self.mapping.get(self.decorated.status.value, self.decorated.status.value)
        self.feedback_message = f"{self.decorated.status.value} -> {mapped}"
        return parse_status(mapped)


def default_leaf(node_type: str, name: str, config: dict[str, Any]) -> py_trees.behaviour.Behaviour:
    if node_type == "success":
        return py_trees.behaviours.Success(name=name)
    if node_type == "failure":
        return py_trees.behaviours.Failure(name=name)
    if node_type == "running":
        return py_trees.behaviours.Running(name=name)

    result = parse_status(str(config.get("result", "SUCCESS")))
    delay_ticks = int(config.get("delay_ticks", 0))
    return TimedStatusLeaf(name=name, result=result, delay_ticks=delay_ticks)

