import pytest
from pydantic import ValidationError

from app.utils.event_helpers import filter_events_by_location, filter_events_by_title
from app.schemas import EventCreate


# ---------- Happy path ----------
def test_valid_event_creation(sample_event_dict):
    event = EventCreate(**sample_event_dict)
    assert event.title == "Python Workshop"
    assert event.capacity == 50


def test_filter_by_location_case_insensitive(prepopulated_event_store):
    result = filter_events_by_location(prepopulated_event_store, "CONSTANTINE")
    assert len(result) == 1
    assert result[0]["title"] == "Python Workshop"


def test_filter_by_title_case_insensitive(prepopulated_event_store):
    result = filter_events_by_title(prepopulated_event_store, "devops")
    assert [e["id"] for e in result] == [2]


def test_filter_no_match_returns_empty(prepopulated_event_store):
    assert filter_events_by_title(prepopulated_event_store, "zzz") == []


# ---------- Boundary values ----------
def test_capacity_lower_bound(sample_event_dict):
    sample_event_dict["capacity"] = 1
    assert EventCreate(**sample_event_dict).capacity == 1


def test_capacity_upper_bound(sample_event_dict):
    sample_event_dict["capacity"] = 10000
    assert EventCreate(**sample_event_dict).capacity == 10000


def test_title_minimum_length(sample_event_dict):
    sample_event_dict["title"] = "abc"  # exactly 3
    assert EventCreate(**sample_event_dict).title == "abc"


def test_capacity_just_above_upper_bound_fails(sample_event_dict):
    sample_event_dict["capacity"] = 10001
    with pytest.raises(ValidationError):
        EventCreate(**sample_event_dict)


# ---------- Negative ----------
def test_short_title_rejected(sample_event_dict):
    sample_event_dict["title"] = "ab"
    with pytest.raises(ValidationError):
        EventCreate(**sample_event_dict)


@pytest.mark.parametrize("bad_capacity", [0, -1, -100])
def test_invalid_capacity_rejected(sample_event_dict, bad_capacity):
    sample_event_dict["capacity"] = bad_capacity
    with pytest.raises(ValidationError):
        EventCreate(**sample_event_dict)