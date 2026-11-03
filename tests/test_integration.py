import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def unique_email(prefix="user"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


# Integration Test 1: Event Creation & Persistence Verification
def test_create_and_fetch_event_integration():
    response = client.post("/events/", json={
        "title": "DevOps Integration Conf",
        "location": "Constantine",
        "date": "2026-12-01",
        "capacity": 200,
    })
    assert response.status_code == 201
    event_id = response.json()["id"]

    get_resp = client.get(f"/events/{event_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "DevOps Integration Conf"


# Integration Test 2: Participant Registration & Event Sign-up Workflow
def test_register_participant_to_event_integration():
    e_resp = client.post("/events/", json={
        "title": "Cybersecurity Workshop",
        "location": "NTIC",
        "date": "2026-11-15",
        "capacity": 50,
    })
    assert e_resp.status_code == 201
    event_id = e_resp.json()["id"]

    p_resp = client.post("/participants/", json={
        "name": "Alice Dev",
        "email": unique_email("alice"),
    })
    assert p_resp.status_code == 201
    part_id = p_resp.json()["id"]

    reg_resp = client.post(f"/events/{event_id}/register/{part_id}")
    assert reg_resp.status_code == 200

    list_resp = client.get(f"/events/{event_id}/participants")
    assert list_resp.status_code == 200
    assert any(p["id"] == part_id for p in list_resp.json())


# Integration Test 3: Edge Case - Registering to Non-Existent Event
def test_register_non_existent_event_returns_404():
    response = client.post("/events/9999/register/1")
    assert response.status_code == 404