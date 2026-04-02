from __future__ import annotations

import ast
import json
from pathlib import Path
from pprint import pformat
import xml.etree.ElementTree as ET
from typing import Any, Mapping

from pydantic import ValidationError

from app.schemas import NodeDTO, TreeUpsertRequest
from app.validation import validate_tree_payload


def _sort_nodes_key(node: NodeDTO) -> tuple[str, int, str]:
    return (node.parent_id or "", node.order_index, node.id)


def _canonical_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonical_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical_json(item) for item in value]
    return value


def _build_edges(nodes: list[NodeDTO]) -> list[dict[str, str]]:
    return [
        {"id": f"{node.parent_id}->{node.id}", "source": node.parent_id, "target": node.id}
        for node in sorted(nodes, key=_sort_nodes_key)
        if node.parent_id
    ]


def _validation_error_message(prefix: str, payload: TreeUpsertRequest) -> str:
    validation = validate_tree_payload(payload)
    if validation.valid:
        return ""
    messages = ", ".join(issue.message for issue in validation.errors)
    return f"{prefix}: {messages}"


def normalize_tree_payload(tree: TreeUpsertRequest | Mapping[str, Any]) -> TreeUpsertRequest:
    if isinstance(tree, TreeUpsertRequest):
        payload = tree
    else:
        payload = TreeUpsertRequest.model_validate(tree)

    nodes = [
        NodeDTO(
            id=node.id,
            type=node.type,
            label=node.label,
            parent_id=node.parent_id,
            position={"x": float(node.position.x), "y": float(node.position.y)},
            config=_canonical_json(node.config),
            order_index=int(node.order_index),
        )
        for node in payload.nodes
    ]
    nodes.sort(key=_sort_nodes_key)

    normalized = TreeUpsertRequest(
        name=payload.name,
        description=payload.description,
        root_node_id=payload.root_node_id,
        nodes=nodes,
        edges=_build_edges(nodes),
    )
    validation = validate_tree_payload(normalized)
    if not validation.valid:
        raise ValueError(_validation_error_message("Invalid behavior tree", normalized))
    if normalized.root_node_id != validation.root_node_id:
        normalized = TreeUpsertRequest(
            name=normalized.name,
            description=normalized.description,
            root_node_id=validation.root_node_id,
            nodes=normalized.nodes,
            edges=normalized.edges,
        )
    return normalized


def _node_to_data(node: NodeDTO) -> dict[str, Any]:
    return {
        "id": node.id,
        "type": node.type.value,
        "label": node.label,
        "parent_id": node.parent_id,
        "position": {
            "x": node.position.x,
            "y": node.position.y,
        },
        "config": _canonical_json(node.config),
        "order_index": node.order_index,
    }


def _tree_to_data(tree: TreeUpsertRequest | Mapping[str, Any]) -> dict[str, Any]:
    payload = normalize_tree_payload(tree)
    return {
        "name": payload.name,
        "description": payload.description,
        "root_node_id": payload.root_node_id,
        "nodes": [_node_to_data(node) for node in payload.nodes],
    }


def _payload_from_mapping(data: Mapping[str, Any], *, source: str) -> TreeUpsertRequest:
    nodes_data = data.get("nodes")
    if not isinstance(nodes_data, list):
        raise ValueError(f"{source} must define a 'nodes' list.")

    try:
        nodes = [NodeDTO.model_validate(node) for node in nodes_data]
    except ValidationError as error:
        raise ValueError(f"{source} contains an invalid node definition.") from error
    return normalize_tree_payload(
        {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "root_node_id": data.get("root_node_id"),
            "nodes": nodes,
            "edges": _build_edges(nodes),
        }
    )


def _json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    return "json"


def _parse_entry_value(entry: ET.Element, node_id: str) -> tuple[str, Any]:
    key = entry.attrib.get("key")
    if not key:
        raise ValueError(f"Node '{node_id}' contains a config entry without a key.")

    raw_value = entry.text or "null"
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise ValueError(f"Node '{node_id}' has invalid JSON in config entry '{key}'.") from error

    expected_type = entry.attrib.get("type")
    actual_type = _json_type_name(value)
    if expected_type and expected_type != actual_type:
        raise ValueError(
            f"Node '{node_id}' config entry '{key}' expected type '{expected_type}' but got '{actual_type}'."
        )
    return key, value


def _required_attr(attributes: Mapping[str, str], key: str, *, context: str) -> str:
    value = attributes.get(key)
    if value is None:
        raise ValueError(f"{context} is missing the '{key}' attribute.")
    return value


def load_xml_tree(path: str | Path) -> TreeUpsertRequest:
    xml_path = Path(path)
    try:
        root = ET.fromstring(xml_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except ET.ParseError as error:
        raise ValueError(f"Malformed XML in '{xml_path.name}': {error}") from error

    if root.tag != "behavior_tree":
        raise ValueError(f"Unexpected XML root '{root.tag}' in '{xml_path.name}'.")

    nodes: list[NodeDTO] = []
    for child in root:
        if child.tag != "node":
            raise ValueError(f"Unsupported element '{child.tag}' in '{xml_path.name}'.")

        node_id = child.attrib.get("id")
        if not node_id:
            raise ValueError(f"A node in '{xml_path.name}' is missing the 'id' attribute.")

        position = {"x": 0.0, "y": 0.0}
        config: dict[str, Any] = {}
        for element in child:
            if element.tag == "position":
                position = {
                    "x": float(element.attrib.get("x", 0)),
                    "y": float(element.attrib.get("y", 0)),
                }
            elif element.tag == "config":
                for entry in element:
                    if entry.tag != "entry":
                        raise ValueError(f"Unsupported config element '{entry.tag}' for node '{node_id}'.")
                    key, value = _parse_entry_value(entry, node_id)
                    config[key] = value
            else:
                raise ValueError(f"Unsupported node element '{element.tag}' for node '{node_id}'.")

        try:
            nodes.append(
                NodeDTO(
                    id=node_id,
                    type=_required_attr(child.attrib, "type", context=f"Node '{node_id}'"),
                    label=_required_attr(child.attrib, "label", context=f"Node '{node_id}'"),
                    parent_id=child.attrib.get("parent_id"),
                    position=position,
                    config=config,
                    order_index=int(child.attrib.get("order_index", 0)),
                )
            )
        except ValidationError as error:
            raise ValueError(f"Node '{node_id}' in '{xml_path.name}' is invalid.") from error

    return normalize_tree_payload(
        {
            "name": root.attrib.get("name", ""),
            "description": root.attrib.get("description", ""),
            "root_node_id": root.attrib.get("root_node_id"),
            "nodes": nodes,
            "edges": _build_edges(nodes),
        }
    )


def load_xml_directory(input_dir: str | Path) -> list[TreeUpsertRequest]:
    directory = Path(input_dir)
    return [load_xml_tree(path) for path in sorted(directory.glob("*.xml"))]


def generate_python(tree: TreeUpsertRequest | Mapping[str, Any]) -> str:
    data = _tree_to_data(tree)
    return f"TREE = {pformat(data, sort_dicts=False, width=100)}\n"


def parse_python(script: str) -> TreeUpsertRequest:
    try:
        module = ast.parse(script, mode="exec")
    except SyntaxError as error:
        raise ValueError("Python script is not valid syntax.") from error

    if len(module.body) != 1 or not isinstance(module.body[0], ast.Assign):
        raise ValueError("Python script must contain exactly one 'TREE = {...}' assignment.")

    assignment = module.body[0]
    if len(assignment.targets) != 1 or not isinstance(assignment.targets[0], ast.Name) or assignment.targets[0].id != "TREE":
        raise ValueError("Python script must assign the tree literal to 'TREE'.")

    try:
        data = ast.literal_eval(assignment.value)
    except Exception as error:
        raise ValueError("Python script must assign a literal value to 'TREE'.") from error

    if not isinstance(data, dict):
        raise ValueError("Python script must assign a dictionary literal to 'TREE'.")

    return _payload_from_mapping(data, source="Python script")


def _encode_scratch_field(value: Any) -> str:
    return json.dumps(_canonical_json(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def generate_scratch(tree: TreeUpsertRequest | Mapping[str, Any]) -> str:
    payload = normalize_tree_payload(tree)
    lines = [
        "\t".join(
            [
                "TREE",
                f"name={_encode_scratch_field(payload.name)}",
                f"description={_encode_scratch_field(payload.description)}",
                f"root={_encode_scratch_field(payload.root_node_id)}",
            ]
        )
    ]
    for node in payload.nodes:
        lines.append(
            "\t".join(
                [
                    "NODE",
                    f"id={_encode_scratch_field(node.id)}",
                    f"type={_encode_scratch_field(node.type.value)}",
                    f"label={_encode_scratch_field(node.label)}",
                    f"parent={_encode_scratch_field(node.parent_id)}",
                    f"order={_encode_scratch_field(node.order_index)}",
                    f"position={_encode_scratch_field({'x': node.position.x, 'y': node.position.y})}",
                    f"config={_encode_scratch_field(node.config)}",
                ]
            )
        )
    return "\n".join(lines) + "\n"


def _parse_scratch_fields(line: str, prefix: str) -> dict[str, Any]:
    parts = line.split("\t")
    if not parts or parts[0] != prefix:
        raise ValueError(f"Expected '{prefix}' line, got '{line}'.")
    values: dict[str, Any] = {}
    for part in parts[1:]:
        if "=" not in part:
            raise ValueError(f"Malformed field '{part}' in '{prefix}' line.")
        key, raw_value = part.split("=", 1)
        try:
            values[key] = json.loads(raw_value)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON value for field '{key}' in '{prefix}' line.") from error
    return values


def _required_field(data: Mapping[str, Any], key: str, *, context: str) -> Any:
    if key not in data:
        raise ValueError(f"{context} is missing the '{key}' field.")
    return data[key]


def parse_scratch(script: str) -> TreeUpsertRequest:
    lines = [line for line in script.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Scratch script is empty.")

    header = _parse_scratch_fields(lines[0], "TREE")
    nodes: list[NodeDTO] = []
    for line in lines[1:]:
        node_data = _parse_scratch_fields(line, "NODE")
        try:
            nodes.append(
                NodeDTO(
                    id=_required_field(node_data, "id", context="Scratch node"),
                    type=_required_field(node_data, "type", context="Scratch node"),
                    label=_required_field(node_data, "label", context="Scratch node"),
                    parent_id=node_data.get("parent"),
                    position=node_data.get("position", {"x": 0, "y": 0}),
                    config=node_data.get("config", {}),
                    order_index=_required_field(node_data, "order", context="Scratch node"),
                )
            )
        except ValidationError as error:
            raise ValueError("Scratch script contains an invalid node definition.") from error

    return normalize_tree_payload(
        {
            "name": header.get("name", ""),
            "description": header.get("description", ""),
            "root_node_id": header.get("root"),
            "nodes": nodes,
            "edges": _build_edges(nodes),
        }
    )
