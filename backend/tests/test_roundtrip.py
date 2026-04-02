from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from app.roundtrip import (
    compare_trees,
    generate_python,
    generate_scratch,
    load_xml_directory,
    parse_python,
    parse_scratch,
    run_roundtrip_directory,
)
from app.schemas import TreeUpsertRequest


def _json_type_name(value):
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


def write_xml_tree(path: Path, payload: dict) -> None:
    root = ET.Element(
        "behavior_tree",
        {
            "name": payload["name"],
            "description": payload["description"],
            "root_node_id": payload["root_node_id"],
        },
    )
    for node in sorted(payload["nodes"], key=lambda item: ((item.get("parent_id") or ""), item["order_index"], item["id"])):
        attributes = {
            "id": node["id"],
            "type": node["type"],
            "label": node["label"],
            "order_index": str(node["order_index"]),
        }
        if node.get("parent_id") is not None:
            attributes["parent_id"] = node["parent_id"]
        node_element = ET.SubElement(root, "node", attributes)

        position = node.get("position") or {"x": 0, "y": 0}
        ET.SubElement(node_element, "position", {"x": str(position["x"]), "y": str(position["y"])})

        config = node.get("config") or {}
        if config:
            config_element = ET.SubElement(node_element, "config")
            for key in sorted(config):
                entry = ET.SubElement(config_element, "entry", {"key": key, "type": _json_type_name(config[key])})
                entry.text = json.dumps(config[key], ensure_ascii=True, sort_keys=True)

    tree = ET.ElementTree(root)
    tree.write(path, encoding="unicode", xml_declaration=False)


def build_complex_tree_payload() -> dict:
    return {
        "name": "Complex Tree",
        "description": "Parallel tree with nested configs",
        "root_node_id": "root",
        "nodes": [
            {
                "id": "root",
                "type": "parallel",
                "label": "Root Parallel",
                "parent_id": None,
                "position": {"x": 320, "y": 40},
                "config": {"policy": "success_on_all", "synchronise": True},
                "order_index": 0,
            },
            {
                "id": "check",
                "type": "condition",
                "label": "Check",
                "parent_id": "root",
                "position": {"x": 120, "y": 220},
                "config": {"result": "SUCCESS", "delay_ticks": 0, "metadata": {"tags": ["gate", "fast"], "threshold": 0.5}},
                "order_index": 0,
            },
            {
                "id": "wrap",
                "type": "decorator",
                "label": "Remap Status",
                "parent_id": "root",
                "position": {"x": 420, "y": 220},
                "config": {"success_to": "FAILURE", "failure_to": "SUCCESS", "running_to": "RUNNING"},
                "order_index": 1,
            },
            {
                "id": "act",
                "type": "action",
                "label": "Act",
                "parent_id": "wrap",
                "position": {"x": 420, "y": 380},
                "config": {"result": "FAILURE", "delay_ticks": 2, "payload": {"message": "hello", "retries": 1}},
                "order_index": 0,
            },
        ],
        "edges": [
            {"id": "root-check", "source": "root", "target": "check"},
            {"id": "root-wrap", "source": "root", "target": "wrap"},
            {"id": "wrap-act", "source": "wrap", "target": "act"},
        ],
    }


def test_load_xml_directory_reads_each_xml_as_separate_tree(tmp_path: Path, sample_tree_payload: dict) -> None:
    alpha = deepcopy(sample_tree_payload)
    alpha["name"] = "Alpha Tree"
    beta = deepcopy(sample_tree_payload)
    beta["name"] = "Beta Tree"

    write_xml_tree(tmp_path / "a.xml", alpha)
    write_xml_tree(tmp_path / "b.xml", beta)

    trees = load_xml_directory(tmp_path)

    assert [tree.name for tree in trees] == ["Alpha Tree", "Beta Tree"]


def test_xml_to_python_roundtrip_matches_original_tree(tmp_path: Path, sample_tree_payload: dict) -> None:
    write_xml_tree(tmp_path / "sample.xml", sample_tree_payload)
    tree = load_xml_directory(tmp_path)[0]

    script = generate_python(tree)
    restored = parse_python(script)
    result = compare_trees(tree, restored)

    assert "TREE =" in script
    assert result.matches is True
    assert result.mismatches == ()


def test_xml_to_scratch_roundtrip_matches_original_tree(tmp_path: Path, sample_tree_payload: dict) -> None:
    write_xml_tree(tmp_path / "sample.xml", sample_tree_payload)
    tree = load_xml_directory(tmp_path)[0]

    script = generate_scratch(tree)
    restored = parse_scratch(script)
    result = compare_trees(tree, restored)

    assert script.startswith("TREE\t")
    assert result.matches is True
    assert result.mismatches == ()


def test_roundtrip_directory_handles_complex_tree_and_writes_outputs(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    write_xml_tree(input_dir / "complex.xml", build_complex_tree_payload())

    reports = run_roundtrip_directory(input_dir, output_dir)

    assert len(reports) == 1
    report = reports[0]
    assert report.tree_name == "Complex Tree"
    assert report.success is True
    assert report.python_result is not None and report.python_result.matches is True
    assert report.scratch_result is not None and report.scratch_result.matches is True
    assert report.python_output_path == output_dir / "complex.py"
    assert report.scratch_output_path == output_dir / "complex.scratch"
    assert report.python_output_path.read_text(encoding="utf-8").startswith("TREE =")
    assert report.scratch_output_path.read_text(encoding="utf-8").startswith("TREE\t")


def test_compare_trees_ignores_position_but_reports_structural_mismatches() -> None:
    original_payload = build_complex_tree_payload()
    original = TreeUpsertRequest(**original_payload)
    restored_payload = deepcopy(original_payload)
    restored_payload["nodes"][0]["position"] = {"x": 999, "y": 999}
    restored_payload["nodes"][1]["label"] = "Changed Label"
    restored_payload["nodes"][1]["parent_id"] = "wrap"
    restored_payload["nodes"][3]["parent_id"] = "root"
    restored_payload["nodes"][3]["order_index"] = 2
    restored_payload["nodes"][3]["config"]["delay_ticks"] = 99

    result = compare_trees(original, TreeUpsertRequest(**restored_payload))
    paths = {mismatch.path for mismatch in result.mismatches}

    assert result.matches is False
    assert "nodes[check].label" in paths
    assert "nodes[check].parent_id" in paths
    assert "nodes[act].order_index" in paths
    assert "nodes[act].config.delay_ticks" in paths
    assert all("position" not in path for path in paths)


def test_run_roundtrip_directory_reports_malformed_xml_without_hiding_valid_files(
    tmp_path: Path,
    sample_tree_payload: dict,
) -> None:
    write_xml_tree(tmp_path / "good.xml", sample_tree_payload)
    (tmp_path / "broken.xml").write_text("<behavior_tree><node>", encoding="utf-8")

    reports = run_roundtrip_directory(tmp_path)

    assert len(reports) == 2
    failed = next(report for report in reports if report.source_path.name == "broken.xml")
    succeeded = next(report for report in reports if report.source_path.name == "good.xml")
    assert failed.source_error is not None
    assert "Malformed XML" in failed.source_error
    assert succeeded.success is True


def test_parse_python_rejects_arbitrary_code() -> None:
    with pytest.raises(ValueError, match="exactly one 'TREE ="):
        parse_python("import os\nTREE = {'name': 'bad', 'description': '', 'root_node_id': None, 'nodes': []}\n")

    with pytest.raises(ValueError, match="literal value"):
        parse_python("TREE = build_tree()\n")


def test_parse_scratch_rejects_invalid_dsl() -> None:
    with pytest.raises(ValueError, match="missing the 'label' field"):
        parse_scratch('TREE\tname="Demo"\tdescription=""\troot="root"\nNODE\tid="root"\ttype="sequence"\torder=0\n')
