from __future__ import annotations

from app.schemas import TreeUpsertRequest
from app.validation import validate_tree_payload


def test_validation_accepts_valid_tree(sample_tree_payload: dict) -> None:
    result = validate_tree_payload(TreeUpsertRequest(**sample_tree_payload))
    assert result.valid is True
    assert result.root_node_id == "root"
    assert result.errors == []


def test_validation_rejects_multiple_roots(sample_tree_payload: dict) -> None:
    sample_tree_payload["nodes"][1]["parent_id"] = None
    sample_tree_payload["edges"] = [{"id": "root-act", "source": "root", "target": "act"}]

    result = validate_tree_payload(TreeUpsertRequest(**sample_tree_payload))

    assert result.valid is False
    assert any("exactly one root" in issue.message.lower() for issue in result.errors)


def test_validation_rejects_cycle(sample_tree_payload: dict) -> None:
    sample_tree_payload["nodes"][0]["parent_id"] = "act"
    sample_tree_payload["edges"].append({"id": "act-root", "source": "act", "target": "root"})

    result = validate_tree_payload(TreeUpsertRequest(**sample_tree_payload))

    assert result.valid is False
    assert any("cycle" in issue.message.lower() for issue in result.errors)


def test_validation_rejects_children_on_leaf(sample_tree_payload: dict) -> None:
    sample_tree_payload["nodes"][2]["type"] = "success"
    sample_tree_payload["nodes"].append(
        {
            "id": "leaf-child",
            "type": "action",
            "label": "Leaf Child",
            "parent_id": "act",
            "position": {"x": 200, "y": 360},
            "config": {"result": "SUCCESS", "delay_ticks": 0},
            "order_index": 0,
        }
    )
    sample_tree_payload["edges"].append({"id": "act-leaf-child", "source": "act", "target": "leaf-child"})

    result = validate_tree_payload(TreeUpsertRequest(**sample_tree_payload))

    assert result.valid is False
    assert any("leaf nodes cannot have children" in issue.message.lower() for issue in result.errors)

