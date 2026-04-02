from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.codecs import (
    generate_python,
    generate_scratch,
    load_xml_directory,
    load_xml_tree,
    normalize_tree_payload,
    parse_python,
    parse_scratch,
)
from app.schemas import TreeUpsertRequest


@dataclass(frozen=True, slots=True)
class _NormalizedNode:
    id: str
    type: str
    label: str
    parent_id: str | None
    order_index: int
    config: Any


@dataclass(frozen=True, slots=True)
class NormalizedTree:
    name: str
    description: str
    root_node_id: str | None
    nodes: tuple[_NormalizedNode, ...]


@dataclass(frozen=True, slots=True)
class ComparisonMismatch:
    path: str
    expected: Any
    actual: Any


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    matches: bool
    mismatches: tuple[ComparisonMismatch, ...] = ()


@dataclass(frozen=True, slots=True)
class RoundTripReport:
    source_path: Path
    tree_name: str | None = None
    source_error: str | None = None
    python_output_path: Path | None = None
    python_result: ComparisonResult | None = None
    python_error: str | None = None
    scratch_output_path: Path | None = None
    scratch_result: ComparisonResult | None = None
    scratch_error: str | None = None

    @property
    def success(self) -> bool:
        return (
            self.source_error is None
            and self.python_error is None
            and self.scratch_error is None
            and self.python_result is not None
            and self.python_result.matches
            and self.scratch_result is not None
            and self.scratch_result.matches
        )


def _to_normalized_tree(tree: TreeUpsertRequest) -> NormalizedTree:
    payload = normalize_tree_payload(tree)
    return NormalizedTree(
        name=payload.name,
        description=payload.description,
        root_node_id=payload.root_node_id,
        nodes=tuple(
            _NormalizedNode(
                id=node.id,
                type=node.type.value,
                label=node.label,
                parent_id=node.parent_id,
                order_index=node.order_index,
                config=node.config,
            )
            for node in payload.nodes
        ),
    )


def _compare_values(path: str, expected: Any, actual: Any, mismatches: list[ComparisonMismatch]) -> None:
    if type(expected) is not type(actual):
        mismatches.append(ComparisonMismatch(path=path, expected=expected, actual=actual))
        return

    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            mismatches.append(ComparisonMismatch(path=f"{path}.{key}", expected=expected[key], actual=None))
        for key in sorted(actual_keys - expected_keys):
            mismatches.append(ComparisonMismatch(path=f"{path}.{key}", expected=None, actual=actual[key]))
        for key in sorted(expected_keys & actual_keys):
            _compare_values(f"{path}.{key}", expected[key], actual[key], mismatches)
        return

    if isinstance(expected, list):
        if len(expected) != len(actual):
            mismatches.append(ComparisonMismatch(path=path, expected=expected, actual=actual))
            return
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual, strict=True)):
            _compare_values(f"{path}[{index}]", expected_item, actual_item, mismatches)
        return

    if expected != actual:
        mismatches.append(ComparisonMismatch(path=path, expected=expected, actual=actual))


def compare_trees(original: TreeUpsertRequest | dict[str, Any], restored: TreeUpsertRequest | dict[str, Any]) -> ComparisonResult:
    try:
        expected_tree = _to_normalized_tree(normalize_tree_payload(original))
        actual_tree = _to_normalized_tree(normalize_tree_payload(restored))
    except ValueError as error:
        return ComparisonResult(
            matches=False,
            mismatches=(ComparisonMismatch(path="tree", expected="valid tree", actual=str(error)),),
        )

    mismatches: list[ComparisonMismatch] = []
    if expected_tree.name != actual_tree.name:
        mismatches.append(ComparisonMismatch(path="name", expected=expected_tree.name, actual=actual_tree.name))
    if expected_tree.description != actual_tree.description:
        mismatches.append(
            ComparisonMismatch(path="description", expected=expected_tree.description, actual=actual_tree.description)
        )
    if expected_tree.root_node_id != actual_tree.root_node_id:
        mismatches.append(
            ComparisonMismatch(
                path="root_node_id",
                expected=expected_tree.root_node_id,
                actual=actual_tree.root_node_id,
            )
        )

    expected_nodes = {node.id: node for node in expected_tree.nodes}
    actual_nodes = {node.id: node for node in actual_tree.nodes}

    for node_id in sorted(expected_nodes.keys() - actual_nodes.keys()):
        mismatches.append(ComparisonMismatch(path=f"nodes[{node_id}]", expected="present", actual="missing"))
    for node_id in sorted(actual_nodes.keys() - expected_nodes.keys()):
        mismatches.append(ComparisonMismatch(path=f"nodes[{node_id}]", expected="missing", actual="present"))

    for node_id in sorted(expected_nodes.keys() & actual_nodes.keys()):
        expected_node = expected_nodes[node_id]
        actual_node = actual_nodes[node_id]
        if expected_node.type != actual_node.type:
            mismatches.append(
                ComparisonMismatch(path=f"nodes[{node_id}].type", expected=expected_node.type, actual=actual_node.type)
            )
        if expected_node.label != actual_node.label:
            mismatches.append(
                ComparisonMismatch(path=f"nodes[{node_id}].label", expected=expected_node.label, actual=actual_node.label)
            )
        if expected_node.parent_id != actual_node.parent_id:
            mismatches.append(
                ComparisonMismatch(
                    path=f"nodes[{node_id}].parent_id",
                    expected=expected_node.parent_id,
                    actual=actual_node.parent_id,
                )
            )
        if expected_node.order_index != actual_node.order_index:
            mismatches.append(
                ComparisonMismatch(
                    path=f"nodes[{node_id}].order_index",
                    expected=expected_node.order_index,
                    actual=actual_node.order_index,
                )
            )
        _compare_values(f"nodes[{node_id}].config", expected_node.config, actual_node.config, mismatches)

    return ComparisonResult(matches=not mismatches, mismatches=tuple(mismatches))


def run_roundtrip_directory(input_dir: str | Path, output_dir: str | Path | None = None) -> list[RoundTripReport]:
    source_dir = Path(input_dir)
    destination_dir = Path(output_dir) if output_dir else None
    if destination_dir is not None:
        destination_dir.mkdir(parents=True, exist_ok=True)

    reports: list[RoundTripReport] = []
    for xml_path in sorted(source_dir.glob("*.xml")):
        tree_name: str | None = None
        python_output_path: Path | None = None
        python_result: ComparisonResult | None = None
        python_error: str | None = None
        scratch_output_path: Path | None = None
        scratch_result: ComparisonResult | None = None
        scratch_error: str | None = None

        try:
            tree = load_xml_tree(xml_path)
            tree_name = tree.name
        except (ValueError, OSError) as error:
            reports.append(RoundTripReport(source_path=xml_path, source_error=str(error)))
            continue

        try:
            python_script = generate_python(tree)
            if destination_dir is not None:
                python_output_path = destination_dir / f"{xml_path.stem}.py"
                python_output_path.write_text(python_script, encoding="utf-8")
            python_result = compare_trees(tree, parse_python(python_script))
        except ValueError as error:
            python_error = str(error)

        try:
            scratch_script = generate_scratch(tree)
            if destination_dir is not None:
                scratch_output_path = destination_dir / f"{xml_path.stem}.scratch"
                scratch_output_path.write_text(scratch_script, encoding="utf-8")
            scratch_result = compare_trees(tree, parse_scratch(scratch_script))
        except ValueError as error:
            scratch_error = str(error)

        reports.append(
            RoundTripReport(
                source_path=xml_path,
                tree_name=tree_name,
                python_output_path=python_output_path,
                python_result=python_result,
                python_error=python_error,
                scratch_output_path=scratch_output_path,
                scratch_result=scratch_result,
                scratch_error=scratch_error,
            )
        )

    return reports
