from __future__ import annotations


def test_healthcheck(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tree_crud_and_execution_flow(client, sample_tree_payload: dict) -> None:
    create_response = client.post("/trees", json=sample_tree_payload)
    assert create_response.status_code == 201
    tree = create_response.json()
    assert tree["is_valid"] is True
    assert tree["node_count"] == 3

    validate_response = client.post(f"/trees/{tree['id']}/validate")
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True

    run_response = client.post(f"/trees/{tree['id']}/run")
    assert run_response.status_code == 201
    session = run_response.json()
    assert session["status"] == "idle"
    assert session["tick_count"] == 0

    tick_response = client.post(f"/sessions/{session['id']}/tick")
    assert tick_response.status_code == 200
    ticked = tick_response.json()
    assert ticked["status"] == "running"
    assert ticked["tick_count"] == 1
    assert ticked["node_statuses"]["act"]["status"] == "running"

    tick_response = client.post(f"/sessions/{session['id']}/tick")
    assert tick_response.status_code == 200
    completed = tick_response.json()
    assert completed["status"] == "success"
    assert completed["tick_count"] == 2

    state_response = client.get(f"/sessions/{session['id']}/state")
    assert state_response.status_code == 200
    assert state_response.json()["tree"]["id"] == tree["id"]

    reset_response = client.post(f"/sessions/{session['id']}/reset")
    assert reset_response.status_code == 200
    reset = reset_response.json()
    assert reset["status"] == "idle"
    assert reset["tick_count"] == 0


def test_invalid_tree_is_saved_as_draft_but_cannot_run(client, sample_tree_payload: dict) -> None:
    sample_tree_payload["nodes"][2]["parent_id"] = None
    sample_tree_payload["edges"] = [{"id": "root-check", "source": "root", "target": "check"}]

    create_response = client.post("/trees", json=sample_tree_payload)
    assert create_response.status_code == 201
    tree = create_response.json()
    assert tree["is_valid"] is False
    assert tree["validation_errors"]

    run_response = client.post(f"/trees/{tree['id']}/run")
    assert run_response.status_code == 400

