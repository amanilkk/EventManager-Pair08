from types import SimpleNamespace
<<<<<<< HEAD
from unittest.mock import MagicMock
from app.routers.participants import router as participants_router
from app.routers.registrations import router as registrations_router
from app.schemas import Participant as ParticipantSchema
from app.schemas import Registration as RegistrationSchema
=======
from unittest.mock import MagicMock, patch

>>>>>>> 943f1a248f5db7a98f9777ab9e23d2ecb4a510f7
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.database import get_db
from app.routers import participants as participants_module
from app.routers import registrations as registrations_module
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
from app.schemas import Participant as ParticipantSchema
from app.schemas import ParticipantCreate
from app.schemas import Registration as RegistrationSchema


def make_event(nb_registered, capacity):
    """Fake event with `nb_registered` registrations."""
    return SimpleNamespace(
        registrations=[object()] * nb_registered,
        capacity=capacity,
    )


def setup_register(mock_db, event, participant, existing):
    """The 3 queries of register_participant, in order."""
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        event, participant, existing,
    ]


def declared_routes(router):
    """{(path, METHOD): route} for every route declared on the router."""
    return {(r.path, m): r for r in router.routes for m in r.methods}


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
    assert result.name == "Amine Benali"
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


def test_register_returns_registration_with_correct_ids(mock_db):
    setup_register(mock_db, make_event(0, 10), MagicMock(), None)
    result = register_participant(5, 7, mock_db)
    assert result.event_id == 5
    assert result.participant_id == 7


def test_list_event_participants_returns_dicts(mock_db):
    regs = [
        SimpleNamespace(participant=SimpleNamespace(id=1, name="Al", email="a@b.com")),
        SimpleNamespace(participant=SimpleNamespace(id=2, name="Bo", email="c@d.com")),
    ]
    mock_db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        registrations=regs
    )
    assert list_event_participants(1, mock_db) == [
        {"id": 1, "name": "Al", "email": "a@b.com"},
        {"id": 2, "name": "Bo", "email": "c@d.com"},
    ]


def test_list_event_participants_empty(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        registrations=[]
    )
    assert list_event_participants(1, mock_db) == []


# ======================= BOUNDARY VALUE =======================
@pytest.mark.parametrize("length", [2, 100])
def test_name_length_accepted(sample_participant_dict, length):
    sample_participant_dict["name"] = "a" * length
    assert len(ParticipantCreate(**sample_participant_dict).name) == length


def test_register_empty_event_succeeds(mock_db):
    """0 registered out of 10."""
    setup_register(mock_db, make_event(0, 10), MagicMock(), None)
    register_participant(1, 2, mock_db)
    mock_db.add.assert_called_once()


def test_register_when_one_seat_left_succeeds(mock_db):
    """current = max - 1: registration goes through."""
    setup_register(mock_db, make_event(9, 10), MagicMock(), None)
    register_participant(1, 2, mock_db)
    mock_db.add.assert_called_once()


def test_register_when_event_exactly_full_returns_409(mock_db):
    """current = max: refused."""
    setup_register(mock_db, make_event(10, 10), MagicMock(), None)
    with pytest.raises(HTTPException) as exc:
        register_participant(1, 2, mock_db)
    assert exc.value.status_code == 409
    assert exc.value.detail == "Event capacity has been reached."
    mock_db.add.assert_not_called()


def test_register_when_event_overfull_returns_409(mock_db):
    """current > max: refused."""
    setup_register(mock_db, make_event(11, 10), MagicMock(), None)
    with pytest.raises(HTTPException) as exc:
        register_participant(1, 2, mock_db)
    assert exc.value.status_code == 409
    assert exc.value.detail == "Event capacity has been reached."


# ======================= NEGATIVE =======================
@pytest.mark.parametrize(
    "bad_email", ["not-an-email", "missing@domain", "@no-user.com", ""]
)
def test_invalid_email_rejected(sample_participant_dict, bad_email):
    sample_participant_dict["email"] = bad_email
    with pytest.raises(ValidationError):
        ParticipantCreate(**sample_participant_dict)


@pytest.mark.parametrize("length", [1, 101])
def test_name_length_rejected(sample_participant_dict, length):
    sample_participant_dict["name"] = "a" * length
    with pytest.raises(ValidationError):
        ParticipantCreate(**sample_participant_dict)


def test_create_participant_duplicate_email_returns_409(mock_db, sample_participant_dict):
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
    with pytest.raises(HTTPException) as exc:
        create_participant(ParticipantCreate(**sample_participant_dict), mock_db)
    assert exc.value.status_code == 409
    assert exc.value.detail == "Email is already registered."
    mock_db.add.assert_not_called()


def test_get_participant_not_found_returns_404(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_participant(999, mock_db)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Participant not found."


def test_delete_participant_not_found_returns_404(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        delete_participant(999, mock_db)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Participant not found."
    mock_db.delete.assert_not_called()


def test_register_event_not_found_returns_404(mock_db):
    mock_db.query.return_value.filter.return_value.first.side_effect = [None]
    with pytest.raises(HTTPException) as exc:
        register_participant(999, 1, mock_db)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Event not found."


def test_register_participant_not_found_returns_404(mock_db):
    setup_register(mock_db, make_event(0, 10), None, None)
    with pytest.raises(HTTPException) as exc:
        register_participant(1, 999, mock_db)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Participant not found."


def test_register_duplicate_registration_returns_409(mock_db):
    setup_register(mock_db, make_event(1, 10), MagicMock(), MagicMock())
    with pytest.raises(HTTPException) as exc:
        register_participant(1, 2, mock_db)
    assert exc.value.status_code == 409
    assert exc.value.detail == "Participant is already registered."
    mock_db.add.assert_not_called()


def test_duplicate_is_checked_before_capacity(mock_db):
    """Full event AND already registered: the duplicate error comes first."""
    setup_register(mock_db, make_event(10, 10), MagicMock(), MagicMock())
    with pytest.raises(HTTPException) as exc:
        register_participant(1, 2, mock_db)
    assert exc.value.detail == "Participant is already registered."


def test_list_event_participants_event_not_found_returns_404(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        list_event_participants(999, mock_db)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Event not found."


# ============ ROUTER DECLARATIONS (kill decorator mutants) ============
def test_participants_router_declaration():
    router = participants_module.router
    assert router.prefix == "/participants"
    assert router.tags == ["Participants"]
    routes = declared_routes(router)
    assert routes[("/participants/", "POST")].status_code == 201
    assert ("/participants/", "GET") in routes
    assert ("/participants/{participant_id}", "GET") in routes
    assert routes[("/participants/{participant_id}", "DELETE")].status_code == 204
    assert len(routes) == 4


def test_registrations_router_declaration():
    router = registrations_module.router
    assert router.prefix == "/events"
    assert router.tags == ["Registrations"]
    routes = declared_routes(router)
    path = "/events/{event_id}/register/{participant_id}"
    assert routes[(path, "POST")].status_code == 201
    assert ("/events/{event_id}/participants", "GET") in routes
    assert len(routes) == 2


# ============ SCHEMAS READING ORM OBJECTS (from_attributes) ============
def test_participant_schema_reads_orm_objects():
    obj = SimpleNamespace(id=1, name="Amine", email="a@b.com")
    assert ParticipantSchema.model_validate(obj).id == 1


def test_registration_schema_reads_orm_objects():
    obj = SimpleNamespace(id=1, event_id=2, participant_id=3)
    assert RegistrationSchema.model_validate(obj).participant_id == 3


# ============ DATABASE SESSION ============
def test_get_db_closes_session():
    fake = MagicMock()
    with patch("app.database.SessionLocal", return_value=fake):
        gen = get_db()
        assert next(gen) is fake
        gen.close()
    fake.close.assert_called_once()
<<<<<<< HEAD

# ===== Mutants 42 and 68: router metadata =====
def test_participants_router_prefix_and_tags():
    assert participants_router.prefix == "/participants"
    assert participants_router.tags == ["Participants"]


def test_registrations_router_prefix_and_tags():
    assert registrations_router.prefix == "/events"
    assert registrations_router.tags == ["Registrations"]


# ===== Mutants 117-118: Participant schema reads ORM objects =====
def test_participant_schema_reads_orm_object():
    orm_obj = SimpleNamespace(id=1, name="Amine", email="amine@example.com")
    schema = ParticipantSchema.model_validate(orm_obj)
    assert schema.id == 1
    assert schema.name == "Amine"


# ===== Mutants 119-120: Registration schema reads ORM objects =====
def test_registration_schema_reads_orm_object():
    orm_obj = SimpleNamespace(id=1, event_id=2, participant_id=3)
    schema = RegistrationSchema.model_validate(orm_obj)
    assert (schema.id, schema.event_id, schema.participant_id) == (1, 2, 3)
=======
def filters(mock_db):
    """SQL text of every .filter(...) call, in call order."""
    return [
        " ".join(
            str(a.compile(compile_kwargs={"literal_binds": True}))
            for a in call.args
        )
        for call in mock_db.query.return_value.filter.call_args_list
    ]


def test_create_participant_looks_up_by_email(mock_db, sample_participant_dict):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    create_participant(ParticipantCreate(**sample_participant_dict), mock_db)
    assert "email = 'amine@example.com'" in filters(mock_db)[0]


def test_get_participant_filters_by_exact_id(mock_db):
    get_participant(5, mock_db)
    assert ".id = 5" in filters(mock_db)[0]


def test_delete_participant_filters_by_exact_id(mock_db):
    delete_participant(5, mock_db)
    assert ".id = 5" in filters(mock_db)[0]


def test_register_queries_use_exact_ids(mock_db):
    setup_register(mock_db, make_event(0, 10), MagicMock(), None)
    register_participant(5, 7, mock_db)
    f = filters(mock_db)
    assert ".id = 5" in f[0]               # event lookup
    assert ".id = 7" in f[1]               # participant lookup
    assert "event_id = 5" in f[2]          # duplicate check
    assert "participant_id = 7" in f[2]


def test_list_event_participants_filters_by_event_id(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        registrations=[]
    )
    list_event_participants(5, mock_db)
    assert ".id = 5" in filters(mock_db)[0]
>>>>>>> 943f1a248f5db7a98f9777ab9e23d2ecb4a510f7
