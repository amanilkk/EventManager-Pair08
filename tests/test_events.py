from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.routers.events import (
    create_event,
    delete_event,
    get_event,
    list_events,
    update_event,
)
from app.schemas import EventCreate, EventUpdate


# ======================= HAPPY PATH =======================
def test_valid_event_creation(sample_event_dict):
    event = EventCreate(**sample_event_dict)
    assert event.title == "Python Workshop"
    assert event.capacity == 50


def test_create_event_success(mock_db, sample_event_dict):
    result = create_event(EventCreate(**sample_event_dict), mock_db)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert result.title == "Python Workshop"


def test_list_events_without_filters(mock_db):
    expected = [MagicMock(), MagicMock()]
    mock_db.query.return_value.order_by.return_value.all.return_value = expected
    result = list_events(search=None, location=None, db=mock_db)
    assert result == expected
    mock_db.query.return_value.filter.assert_not_called()


def test_list_events_with_search_filter(mock_db):
    expected = [MagicMock()]
    chain = mock_db.query.return_value.filter.return_value
    chain.order_by.return_value.all.return_value = expected
    result = list_events(search="python", location=None, db=mock_db)
    assert result == expected
    mock_db.query.return_value.filter.assert_called_once()


def test_list_events_with_search_and_location(mock_db):
    expected = [MagicMock()]
    chain = mock_db.query.return_value.filter.return_value.filter.return_value
    chain.order_by.return_value.all.return_value = expected
    result = list_events(search="python", location="constantine", db=mock_db)
    assert result == expected


def test_list_events_filter_is_case_insensitive(mock_db):
    """Le filtre utilise ilike => LOWER(...) LIKE LOWER(...) en SQL."""
    list_events(search="PyThOn", location=None, db=mock_db)
    expression = mock_db.query.return_value.filter.call_args[0][0]
    assert "lower(" in str(expression).lower()


def test_get_event_found(mock_db):
    fake = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = fake
    assert get_event(1, mock_db) is fake


def test_update_event_success(mock_db, sample_event_dict):
    existing = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = existing
    sample_event_dict["title"] = "New Title"
    update_event(1, EventUpdate(**sample_event_dict), mock_db)
    assert existing.title == "New Title"
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(existing)


def test_delete_event_success(mock_db):
    existing = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = existing
    delete_event(1, mock_db)
    mock_db.delete.assert_called_once_with(existing)
    mock_db.commit.assert_called_once()


# ======================= BOUNDARY VALUE =======================
def test_capacity_lower_bound(sample_event_dict):
    sample_event_dict["capacity"] = 1
    assert EventCreate(**sample_event_dict).capacity == 1


def test_capacity_upper_bound(sample_event_dict):
    sample_event_dict["capacity"] = 10000
    assert EventCreate(**sample_event_dict).capacity == 10000


def test_title_minimum_length(sample_event_dict):
    sample_event_dict["title"] = "abc"
    assert EventCreate(**sample_event_dict).title == "abc"


def test_capacity_just_above_upper_bound_fails(sample_event_dict):
    sample_event_dict["capacity"] = 10001
    with pytest.raises(ValidationError):
        EventCreate(**sample_event_dict)


def test_create_event_today_is_allowed(mock_db, sample_event_dict):
    """Limite exacte : aujourd'hui est accepté (la règle est `<`, pas `<=`)."""
    sample_event_dict["date"] = date.today()
    result = create_event(EventCreate(**sample_event_dict), mock_db)
    mock_db.add.assert_called_once()
    assert result.date == date.today()


def test_create_event_yesterday_is_rejected(mock_db, sample_event_dict):
    """Juste en dessous de la limite : hier est refusé."""
    sample_event_dict["date"] = date.today() - timedelta(days=1)
    with pytest.raises(HTTPException) as exc:
        create_event(EventCreate(**sample_event_dict), mock_db)
    assert exc.value.status_code == 400


def test_update_event_today_is_allowed(mock_db, sample_event_dict):
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
    sample_event_dict["date"] = date.today()
    update_event(1, EventUpdate(**sample_event_dict), mock_db)
    mock_db.commit.assert_called_once()


# ======================= NEGATIVE =======================
def test_short_title_rejected(sample_event_dict):
    sample_event_dict["title"] = "ab"
    with pytest.raises(ValidationError):
        EventCreate(**sample_event_dict)


@pytest.mark.parametrize("bad_capacity", [0, -1, -100])
def test_invalid_capacity_rejected(sample_event_dict, bad_capacity):
    sample_event_dict["capacity"] = bad_capacity
    with pytest.raises(ValidationError):
        EventCreate(**sample_event_dict)


def test_create_event_past_date_writes_nothing(mock_db, sample_event_dict):
    sample_event_dict["date"] = date.today() - timedelta(days=30)
    with pytest.raises(HTTPException) as exc:
        create_event(EventCreate(**sample_event_dict), mock_db)
    assert exc.value.status_code == 400
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


def test_get_event_not_found_returns_404(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_event(999, mock_db)
    assert exc.value.status_code == 404


def test_update_event_not_found_returns_404(mock_db, sample_event_dict):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        update_event(999, EventUpdate(**sample_event_dict), mock_db)
    assert exc.value.status_code == 404
    mock_db.commit.assert_not_called()


def test_update_event_past_date_returns_400(mock_db, sample_event_dict):
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
    sample_event_dict["date"] = date.today() - timedelta(days=1)
    with pytest.raises(HTTPException) as exc:
        update_event(1, EventUpdate(**sample_event_dict), mock_db)
    assert exc.value.status_code == 400
    mock_db.commit.assert_not_called()


def test_delete_event_not_found_returns_404(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        delete_event(999, mock_db)
    assert exc.value.status_code == 404
    mock_db.delete.assert_not_called()