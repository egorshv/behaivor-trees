from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'test.db'}",
            cors_origins=["http://localhost:5173"],
        )
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_tree_payload() -> dict:
    return {
        "name": "Example Tree",
        "description": "Simple sequence tree",
        "root_node_id": "root",
        "nodes": [
            {
                "id": "root",
                "type": "sequence",
                "label": "Root",
                "parent_id": None,
                "position": {"x": 100, "y": 50},
                "config": {"memory": True},
                "order_index": 0,
            },
            {
                "id": "check",
                "type": "condition",
                "label": "Check",
                "parent_id": "root",
                "position": {"x": 50, "y": 200},
                "config": {"result": "SUCCESS", "delay_ticks": 0},
                "order_index": 0,
            },
            {
                "id": "act",
                "type": "action",
                "label": "Act",
                "parent_id": "root",
                "position": {"x": 180, "y": 200},
                "config": {"result": "SUCCESS", "delay_ticks": 1},
                "order_index": 1,
            },
        ],
        "edges": [
            {"id": "root-check", "source": "root", "target": "check"},
            {"id": "root-act", "source": "root", "target": "act"},
        ],
    }

