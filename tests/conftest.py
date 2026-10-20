from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_event_dict():
    """A valid event payload."""
    return {
        "title": "Python Workshop",
        "description": "Intro to Python for beginners",
        "date": date.today() + timedelta(days=30),
        "location": "Constantine",
        "capacity": 50,
    }


@pytest.fixture
def sample_participant_dict():
    """A valid participant payload."""
    return {"name": "Amine Benali", "email": "amine@example.com"}


@pytest.fixture
def mock_event_store():
    """In-memory repository with teardown."""
    store = []
    yield store
    store.clear()


@pytest.fixture
def prepopulated_event_store(mock_event_store):
    """Chained fixture: the empty store, filled with 3 events."""
    future = date.today() + timedelta(days=15)
    mock_event_store.extend(
        [
            {"id": 1, "title": "Python Workshop", "date": future,
             "location": "Constantine", "capacity": 50},
            {"id": 2, "title": "DevOps Summit", "date": future,
             "location": "Algiers", "capacity": 200},
            {"id": 3, "title": "Cyber Security Conference", "date": future,
             "location": "Oran", "capacity": 500},
        ]
    )
    return mock_event_store


@pytest.fixture
def mock_db():
    """Fausse session SQLAlchemy : aucune vraie base de données."""
    return MagicMock()


@pytest.fixture(autouse=True)
def global_environment_logger():
    """Runs around EVERY test (visible with `pytest -s`)."""
    print("\n[SETUP] test starting")
    yield
    print("[TEARDOWN] test finished")