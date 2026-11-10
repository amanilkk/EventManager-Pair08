
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


# Database fixture for integration tests
@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


# Helper function to create a future event payload
def event_payload():
    return {
        "title": "DevOps Integration Conf",
        "location": "Constantine",
        "date": (date.today() + timedelta(days=30)).isoformat(),
        "capacity": 200
    }


# Integration Test 1: Event Creation & Persistence
def test_create_and_fetch_event_integration(client):

    response = client.post(
        "/events/",
        json=event_payload()
    )

    assert response.status_code == 201

    event_id = response.json()["id"]

    get_resp = client.get(f"/events/{event_id}")

    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "DevOps Integration Conf"
    assert get_resp.json()["location"] == "Constantine"


# Integration Test 2: Participant Registration Workflow
def test_register_participant_to_event_integration(client):

    # 1. Create an event
    e_resp = client.post(
        "/events/",
        json={
            "title": "Cybersecurity Workshop",
            "location": "NTIC",
            "date": (date.today() + timedelta(days=30)).isoformat(),
            "capacity": 50
        }
    )

    assert e_resp.status_code == 201
    event_id = e_resp.json()["id"]

    # 2. Create a participant
    p_resp = client.post(
        "/participants/",
        json={
            "name": "Alice Dev",
            "email": "alice@example.com"
        }
    )

    assert p_resp.status_code == 201
    part_id = p_resp.json()["id"]

    # 3. Register the participant
    reg_resp = client.post(
        f"/events/{event_id}/register/{part_id}"
    )

    assert reg_resp.status_code == 201

    # 4. Verify the attendee list
    list_resp = client.get(
        f"/events/{event_id}/participants"
    )

    assert list_resp.status_code == 200
    assert any(
        p["id"] == part_id
        for p in list_resp.json()
    )


# Integration Test 3: Non-existent Event
def test_register_non_existent_event_returns_404(client):

    response = client.post("/events/9999/register/1")

    assert response.status_code == 404
