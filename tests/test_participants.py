from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from unittest.mock import patch
from app.database import get_db
from app.routers.participants import (
    create_participant,
    delete_participant,
    get_participant,
    list_participants,
)
from app.routers.registrations import (
    list_event_participants,
    register_participant,
)
from app.schemas import ParticipantCreate


def make_event(nb_registered, capacity):
    """Faux événement avec `nb_registered` inscriptions."""
    return SimpleNamespace(
        registrations=[object()] * nb_registered,
        capacity=capacity,
    )


def setup_register(mock_db, event, participant, existing):
    """Les 3 requêtes de register_participant, dans l'ordre."""
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        event, participant, existing,
    ]


# ======================= HAPPY PATH =======================
def test_valid_participant_creation(sample_participant_dict):
    p = ParticipantCreate(**sample_participant_dict)
    assert p.name == "Amine Benali"
    assert p.email == "amine@example.com"


def test_create_participant_success(mock_db, sample_participant_dict):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    result = create_participant(ParticipantCreate(**sample_participant_dict), mock_db)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert result.email == "amine@example.com"


def test_list_participants_returns_all(mock_db):
    expected = [MagicMock(), MagicMock()]
    mock_db.query.return_value.order_by.return_value.all.return_value = expected
    assert list_participants(mock_db) == expected


def test_get_participant_found(mock_db):
    fake = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = fake
    assert get_participant(1, mock_db) is fake


def test_delete_participant_success(mock_db):
    fake = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = fake
    delete_participant(1, mock_db)
    mock_db.delete.assert_called_once_with(fake)
    mock_db.commit.assert_called_once()


def test_register_participant_success(mock_db):
    setup_register(mock_db, make_event(3, 10), MagicMock(), None)
    register_participant(1, 2, mock_db)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


def test_list_event_participants_returns_dicts(mock_db):
    reg = SimpleNamespace(
        participant=SimpleNamespace(id=7, name="Amine", email="a@b.com")
    )
    event = SimpleNamespace(registrations=[reg])
    mock_db.query.return_value.filter.return_value.first.return_value = event
    assert list_event_participants(1, mock_db) == [
        {"id": 7, "name": "Amine", "email": "a@b.com"}
    ]


# ======================= BOUNDARY VALUE =======================
def test_name_exactly_two_characters(sample_participant_dict):
    sample_participant_dict["name"] = "Al"
    assert ParticipantCreate(**sample_participant_dict).name == "Al"


def test_register_empty_event_succeeds(mock_db):
    """0 inscrit sur 10."""
    setup_register(mock_db, make_event(0, 10), MagicMock(), None)
    register_participant(1, 2, mock_db)
    mock_db.add.assert_called_once()


def test_register_when_one_seat_left_succeeds(mock_db):
    """current = max - 1 : l'inscription passe."""
    setup_register(mock_db, make_event(9, 10), MagicMock(), None)
    register_participant(1, 2, mock_db)
    mock_db.add.assert_called_once()


def test_register_when_event_exactly_full_returns_409(mock_db):
    """current = max : refusé."""
    setup_register(mock_db, make_event(10, 10), MagicMock(), None)
    with pytest.raises(HTTPException) as exc:
        register_participant(1, 2, mock_db)
    assert exc.value.status_code == 409
    mock_db.add.assert_not_called()


def test_register_when_event_overfull_returns_409(mock_db):
    """current > max : refusé."""
    setup_register(mock_db, make_event(11, 10), MagicMock(), None)
    with pytest.raises(HTTPException) as exc:
        register_participant(1, 2, mock_db)
    assert exc.value.status_code == 409


# ======================= NEGATIVE =======================
@pytest.mark.parametrize(
    "bad_email", ["not-an-email", "missing@domain", "@no-user.com", ""]
)
def test_invalid_email_rejected(sample_participant_dict, bad_email):
    sample_participant_dict["email"] = bad_email
    with pytest.raises(ValidationError):
        ParticipantCreate(**sample_participant_dict)


def test_short_name_rejected(sample_participant_dict):
    sample_participant_dict["name"] = "A"
    with pytest.raises(ValidationError):
        ParticipantCreate(**sample_participant_dict)


def test_create_participant_duplicate_email_returns_409(mock_db, sample_participant_dict):
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
    with pytest.raises(HTTPException) as exc:
        create_participant(ParticipantCreate(**sample_participant_dict), mock_db)
    assert exc.value.status_code == 409
    mock_db.add.assert_not_called()


def test_get_participant_not_found_returns_404(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_participant(999, mock_db)
    assert exc.value.status_code == 404


def test_delete_participant_not_found_returns_404(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        delete_participant(999, mock_db)
    assert exc.value.status_code == 404
    mock_db.delete.assert_not_called()


def test_register_event_not_found_returns_404(mock_db):
    mock_db.query.return_value.filter.return_value.first.side_effect = [None]
    with pytest.raises(HTTPException) as exc:
        register_participant(999, 1, mock_db)
    assert exc.value.status_code == 404


def test_register_participant_not_found_returns_404(mock_db):
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        make_event(0, 10), None,
    ]
    with pytest.raises(HTTPException) as exc:
        register_participant(1, 999, mock_db)
    assert exc.value.status_code == 404


def test_register_duplicate_registration_returns_409(mock_db):
    setup_register(mock_db, make_event(1, 10), MagicMock(), MagicMock())
    with pytest.raises(HTTPException) as exc:
        register_participant(1, 2, mock_db)
    assert exc.value.status_code == 409
    mock_db.add.assert_not_called()


def test_list_event_participants_event_not_found_returns_404(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        list_event_participants(999, mock_db)
    assert exc.value.status_code == 404

@pytest.mark.parametrize("name, ok", [("A", False), ("Al", True),
                                      ("a" * 100, True), ("a" * 101, False)])
def test_name_length_bounds(sample_participant_dict, name, ok):
    sample_participant_dict["name"] = name
    if ok:
        assert ParticipantCreate(**sample_participant_dict).name == name
    else:
        with pytest.raises(ValidationError):
            ParticipantCreate(**sample_participant_dict)


def test_register_duplicate_has_exact_detail(mock_db):
    setup_register(mock_db, make_event(1, 10), MagicMock(), MagicMock())
    with pytest.raises(HTTPException) as exc:
        register_participant(1, 2, mock_db)
    assert exc.value.detail == "Participant is already registered."


def test_register_full_has_exact_detail(mock_db):
    setup_register(mock_db, make_event(10, 10), MagicMock(), None)
    with pytest.raises(HTTPException) as exc:
        register_participant(1, 2, mock_db)
    assert exc.value.detail == "Event capacity has been reached."


def test_get_db_closes_session():
    fake = MagicMock()
    with patch("app.database.SessionLocal", return_value=fake):
        gen = get_db()
        assert next(gen) is fake
        gen.close()
    fake.close.assert_called_once()