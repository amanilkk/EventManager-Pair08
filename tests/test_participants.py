
import pytest
from pydantic import ValidationError

from app.schemas import ParticipantCreate
from app.utils.registration_helpers import (
    has_available_capacity,
    check_duplicate_registration,
)


# Happy path: valid participant
def test_valid_participant(sample_participant_dict):
    participant = ParticipantCreate(**sample_participant_dict)

    assert participant.name == sample_participant_dict["name"]
    assert str(participant.email) == sample_participant_dict["email"]


# Happy path: capacity is available
def test_capacity_available():
    assert has_available_capacity(4, 5) is True


# Happy path: new registration is not a duplicate
def test_new_registration_allowed():
    check_duplicate_registration([1, 2, 3], 4)


# Boundary: one place remains
def test_capacity_one_place_remaining():
    assert has_available_capacity(9, 10) is True


# Boundary: capacity exactly reached
def test_capacity_reached():
    assert has_available_capacity(10, 10) is False


# Boundary: capacity exceeded
def test_capacity_exceeded():
    assert has_available_capacity(11, 10) is False


# Negative: invalid email
def test_invalid_email(sample_participant_dict):
    data = sample_participant_dict.copy()
    data["email"] = "not-an-email"

    with pytest.raises(ValidationError):
        ParticipantCreate(**data)


# Negative: name too short
def test_name_too_short(sample_participant_dict):
    data = sample_participant_dict.copy()
    data["name"] = "A"

    with pytest.raises(ValidationError):
        ParticipantCreate(**data)


# Negative: duplicate registration
def test_duplicate_registration():
    with pytest.raises(ValueError, match="already registered"):
        check_duplicate_registration([1, 2, 3], 2)


# Boundary: minimum valid name length
def test_name_minimum_length(sample_participant_dict):
    data = sample_participant_dict.copy()
    data["name"] = "Al"

    participant = ParticipantCreate(**data)

    assert participant.name == "Al"

from datetime import date, timedelta


def test_create_participant_api(client):
    response = client.post(
        "/participants/",
        json={"name": "Amira", "email": "amira@example.com"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Amira"
    assert response.json()["email"] == "amira@example.com"


def test_duplicate_email_api(client):
    payload = {"name": "Amira", "email": "amira@example.com"}

    first = client.post("/participants/", json=payload)
    second = client.post("/participants/", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_list_participants_api(client):
    client.post(
        "/participants/",
        json={"name": "Amira", "email": "amira@example.com"},
    )

    response = client.get("/participants/")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_participant_api(client):
    created = client.post(
        "/participants/",
        json={"name": "Amira", "email": "amira@example.com"},
    )
    participant_id = created.json()["id"]

    response = client.get(f"/participants/{participant_id}")

    assert response.status_code == 200
    assert response.json()["id"] == participant_id


def test_get_missing_participant_api(client):
    response = client.get("/participants/9999")

    assert response.status_code == 404


def test_delete_participant_api(client):
    created = client.post(
        "/participants/",
        json={"name": "Amira", "email": "amira@example.com"},
    )
    participant_id = created.json()["id"]

    response = client.delete(f"/participants/{participant_id}")

    assert response.status_code == 204
    assert client.get(f"/participants/{participant_id}").status_code == 404


def test_delete_missing_participant_api(client):
    response = client.delete("/participants/9999")

    assert response.status_code == 404