
import pytest
from pydantic import ValidationError

from app.schemas import EventBase
from app.utils.event_helpers import (
    filter_events_by_location,
    filter_events_by_title,
)


@pytest.fixture
def sample_events():
    return [
        {
            "title": "Cybersecurity Conference",
            "location": "Alger",
        },
        {
            "title": "Python Workshop",
            "location": "Oran",
        },
        {
            "title": "Network Security",
            "location": "Alger Centre",
        },
    ]


# --- Tests positifs ---

def test_filter_events_by_location(sample_events):
    result = filter_events_by_location(sample_events, "Alger")

    assert len(result) == 2
    assert all("Alger" in event["location"] for event in result)


def test_filter_events_by_title(sample_events):
    result = filter_events_by_title(sample_events, "Security")

    assert len(result) == 2


# --- Tests des limites ---

def test_filter_location_case_insensitive(sample_events):
    result = filter_events_by_location(sample_events, "ALGER")

    assert len(result) == 2


def test_filter_title_case_insensitive(sample_events):
    result = filter_events_by_title(sample_events, "cybersecurity")

    assert len(result) == 1


def test_filter_returns_empty_list(sample_events):
    result = filter_events_by_title(sample_events, "Nonexistent")

    assert result == []


# --- Tests négatifs ---

def test_event_title_too_short():
    with pytest.raises(ValidationError):
        EventBase(
            title="AB",
            description="Test",
            date="2027-05-20",
            location="Alger",
            capacity=50,
        )


def test_event_capacity_too_low():
    with pytest.raises(ValidationError):
        EventBase(
            title="Valid Event",
            description="Test",
            date="2027-05-20",
            location="Alger",
            capacity=0,
        )

def test_event_capacity_minimum_valid():
    event = EventBase(
        title="Valid Event",
        description="Test",
        date="2027-05-20",
        location="Alger",
        capacity=1,
    )

    assert event.capacity == 1


def test_event_capacity_maximum_valid():
    event = EventBase(
        title="Valid Event",
        description="Test",
        date="2027-05-20",
        location="Alger",
        capacity=10000,
    )

    assert event.capacity == 10000


def test_event_capacity_too_high():
    with pytest.raises(ValidationError):
        EventBase(
            title="Valid Event",
            description="Test",
            date="2027-05-20",
            location="Alger",
            capacity=10001,
        )


def test_event_title_minimum_valid():
    event = EventBase(
        title="ABC",
        description="Test",
        date="2027-05-20",
        location="Alger",
        capacity=10,
    )

    assert event.title == "ABC"