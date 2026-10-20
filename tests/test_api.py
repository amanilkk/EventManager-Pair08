"""Tests d'intégration légers (SQLite en mémoire) - Lab 3.

Objectif : tuer les mutants que les tests unitaires avec MagicMock laissent
survivre (codes HTTP des décorateurs, messages `detail`, motifs ilike,
ordre de tri, route racine, cascade...).
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def event_payload(**overrides):
    payload = {
        "title": "Python Workshop",
        "description": "Intro",
        "date": (date.today() + timedelta(days=30)).isoformat(),
        "location": "Constantine",
        "capacity": 50,
    }
    payload.update(overrides)
    return payload


def participant_payload(**overrides):
    payload = {"name": "Amine Benali", "email": "amine@example.com"}
    payload.update(overrides)
    return payload


def make_event(client, **overrides):
    r = client.post("/events/", json=event_payload(**overrides))
    assert r.status_code == 201
    return r.json()


def make_participant(client, **overrides):
    r = client.post("/participants/", json=participant_payload(**overrides))
    assert r.status_code == 201
    return r.json()


# ============================ ROOT ============================
def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Welcome to Event Manager API"}


# ============================ EVENTS ============================
def test_create_event_returns_201_and_body(client):
    r = client.post("/events/", json=event_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 1
    assert body["title"] == "Python Workshop"
    assert body["location"] == "Constantine"
    assert body["capacity"] == 50


def test_create_event_past_date_detail(client):
    past = (date.today() - timedelta(days=1)).isoformat()
    r = client.post("/events/", json=event_payload(date=past))
    assert r.status_code == 400
    assert r.json()["detail"] == "Event date cannot be in the past."


def test_create_event_today_ok(client):
    r = client.post("/events/", json=event_payload(date=date.today().isoformat()))
    assert r.status_code == 201


def test_create_event_invalid_payload_422(client):
    assert client.post("/events/", json=event_payload(capacity=0)).status_code == 422
    assert client.post("/events/", json=event_payload(capacity=10001)).status_code == 422
    assert client.post("/events/", json=event_payload(title="ab")).status_code == 422
    assert client.post("/events/", json=event_payload(location="a")).status_code == 422


def test_create_event_boundaries_accepted(client):
    assert client.post("/events/", json=event_payload(capacity=1)).status_code == 201
    assert client.post("/events/", json=event_payload(capacity=10000)).status_code == 201
    assert client.post("/events/", json=event_payload(title="abc")).status_code == 201
    assert client.post("/events/", json=event_payload(location="ab")).status_code == 201


def test_list_events_empty(client):
    r = client.get("/events/")
    assert r.status_code == 200
    assert r.json() == []


def test_list_events_ordered_by_date(client):
    late = (date.today() + timedelta(days=60)).isoformat()
    soon = (date.today() + timedelta(days=5)).isoformat()
    make_event(client, title="Late event", date=late)
    make_event(client, title="Soon event", date=soon)
    titles = [e["title"] for e in client.get("/events/").json()]
    assert titles == ["Soon event", "Late event"]


def test_list_events_search_matches_anywhere_case_insensitive(client):
    make_event(client, title="Python Workshop", location="Constantine")
    make_event(client, title="DevOps Summit", location="Algiers")
    # fin de mot (impose le % de gauche), début de mot (impose le % de droite)
    assert len(client.get("/events/", params={"search": "shop"}).json()) == 1
    assert len(client.get("/events/", params={"search": "Pyth"}).json()) == 1
    assert len(client.get("/events/", params={"search": "PYTHON"}).json()) == 1
    assert client.get("/events/", params={"search": "zzz"}).json() == []


def test_list_events_location_only(client):
    make_event(client, title="Python Workshop", location="Constantine")
    make_event(client, title="DevOps Summit", location="Algiers")
    r = client.get("/events/", params={"location": "ALGI"})
    assert [e["title"] for e in r.json()] == ["DevOps Summit"]
    assert client.get("/events/", params={"location": "giers"}).json()[0]["title"] == "DevOps Summit"
    assert client.get("/events/", params={"location": "nowhere"}).json() == []


def test_list_events_search_and_location_combined(client):
    make_event(client, title="Python Workshop", location="Constantine")
    make_event(client, title="Python Summit", location="Algiers")
    r = client.get("/events/", params={"search": "python", "location": "constantine"})
    assert [e["location"] for e in r.json()] == ["Constantine"]
    r = client.get("/events/", params={"search": "devops", "location": "constantine"})
    assert r.json() == []


def test_get_event_found_and_not_found(client):
    ev = make_event(client)
    r = client.get(f"/events/{ev['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Python Workshop"
    r = client.get("/events/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Event not found."


def test_update_event_success_persisted(client):
    ev = make_event(client)
    r = client.put(f"/events/{ev['id']}", json=event_payload(title="New Title", capacity=7))
    assert r.status_code == 200
    assert r.json()["title"] == "New Title"
    again = client.get(f"/events/{ev['id']}").json()
    assert again["title"] == "New Title"
    assert again["capacity"] == 7


def test_update_event_not_found_detail(client):
    r = client.put("/events/999", json=event_payload())
    assert r.status_code == 404
    assert r.json()["detail"] == "Event not found."


def test_update_event_past_date_detail(client):
    ev = make_event(client)
    past = (date.today() - timedelta(days=1)).isoformat()
    r = client.put(f"/events/{ev['id']}", json=event_payload(date=past))
    assert r.status_code == 400
    assert r.json()["detail"] == "Event date cannot be in the past."


def test_delete_event_success(client):
    ev = make_event(client)
    r = client.delete(f"/events/{ev['id']}")
    assert r.status_code == 204
    assert client.get(f"/events/{ev['id']}").status_code == 404


def test_delete_event_not_found_detail(client):
    r = client.delete("/events/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Event not found."


# ============================ PARTICIPANTS ============================
def test_create_participant_201(client):
    r = client.post("/participants/", json=participant_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 1
    assert body["name"] == "Amine Benali"
    assert body["email"] == "amine@example.com"


def test_create_participant_duplicate_email(client):
    make_participant(client)
    r = client.post("/participants/", json=participant_payload(name="Autre"))
    assert r.status_code == 409
    assert r.json()["detail"] == "Email is already registered."


def test_create_participant_invalid_422(client):
    assert client.post("/participants/", json=participant_payload(email="bad")).status_code == 422
    assert client.post("/participants/", json=participant_payload(name="A")).status_code == 422


def test_list_participants_ordered_by_name(client):
    make_participant(client, name="Zineb", email="z@example.com")
    make_participant(client, name="Amine", email="a@example.com")
    names = [p["name"] for p in client.get("/participants/").json()]
    assert names == ["Amine", "Zineb"]


def test_get_participant_found_and_not_found(client):
    p = make_participant(client)
    r = client.get(f"/participants/{p['id']}")
    assert r.status_code == 200
    assert r.json()["email"] == "amine@example.com"
    r = client.get("/participants/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Participant not found."


def test_delete_participant_success_and_not_found(client):
    p = make_participant(client)
    assert client.delete(f"/participants/{p['id']}").status_code == 204
    assert client.get(f"/participants/{p['id']}").status_code == 404
    r = client.delete("/participants/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Participant not found."


# ============================ REGISTRATIONS ============================
def test_register_participant_201(client):
    ev = make_event(client)
    p = make_participant(client)
    r = client.post(f"/events/{ev['id']}/register/{p['id']}")
    assert r.status_code == 201
    body = r.json()
    assert body["event_id"] == ev["id"]
    assert body["participant_id"] == p["id"]


def test_register_event_not_found_detail(client):
    p = make_participant(client)
    r = client.post(f"/events/999/register/{p['id']}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Event not found."


def test_register_participant_not_found_detail(client):
    ev = make_event(client)
    r = client.post(f"/events/{ev['id']}/register/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Participant not found."


def test_register_duplicate_detail(client):
    ev = make_event(client)
    p = make_participant(client)
    client.post(f"/events/{ev['id']}/register/{p['id']}")
    r = client.post(f"/events/{ev['id']}/register/{p['id']}")
    assert r.status_code == 409
    assert r.json()["detail"] == "Participant is already registered."


def test_register_when_full_detail(client):
    ev = make_event(client, capacity=1)
    p1 = make_participant(client, email="p1@example.com")
    p2 = make_participant(client, name="Second", email="p2@example.com")
    assert client.post(f"/events/{ev['id']}/register/{p1['id']}").status_code == 201
    r = client.post(f"/events/{ev['id']}/register/{p2['id']}")
    assert r.status_code == 409
    assert r.json()["detail"] == "Event capacity has been reached."


def test_register_last_seat_allowed(client):
    ev = make_event(client, capacity=2)
    p1 = make_participant(client, email="p1@example.com")
    p2 = make_participant(client, name="Second", email="p2@example.com")
    assert client.post(f"/events/{ev['id']}/register/{p1['id']}").status_code == 201
    assert client.post(f"/events/{ev['id']}/register/{p2['id']}").status_code == 201


def test_list_event_participants(client):
    ev = make_event(client)
    p = make_participant(client)
    client.post(f"/events/{ev['id']}/register/{p['id']}")
    r = client.get(f"/events/{ev['id']}/participants")
    assert r.status_code == 200
    assert r.json() == [{"id": p["id"], "name": "Amine Benali", "email": "amine@example.com"}]


def test_list_event_participants_empty_and_not_found(client):
    ev = make_event(client)
    assert client.get(f"/events/{ev['id']}/participants").json() == []
    r = client.get("/events/999/participants")
    assert r.status_code == 404
    assert r.json()["detail"] == "Event not found."


def test_deleting_event_cascades_registrations(client):
    ev = make_event(client)
    p = make_participant(client)
    client.post(f"/events/{ev['id']}/register/{p['id']}")
    assert client.delete(f"/events/{ev['id']}").status_code == 204
    # le participant existe toujours, mais il peut s'inscrire à un nouvel événement
    ev2 = make_event(client)
    assert client.post(f"/events/{ev2['id']}/register/{p['id']}").status_code == 201