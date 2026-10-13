import pytest
from pydantic import ValidationError

from app.utils.registration_helpers import check_duplicate_registration, has_available_capacity
from app.schemas import ParticipantCreate


# ---------- Happy path (≥ 2) ----------
def test_valid_participant_creation(sample_participant_dict):
    p = ParticipantCreate(**sample_participant_dict)
    assert p.name == sample_participant_dict["name"]
    assert p.email == sample_participant_dict["email"]
    
def test_capacity_available_when_not_full():
    assert has_available_capacity(5, 10) is True


def test_no_duplicate_registration_passes():
    check_duplicate_registration([1, 2, 3], 4)  # must not raise


# ---------- Boundary values (≥ 3) ----------
def test_capacity_one_below_max():
    assert has_available_capacity(9, 10) is True      # max - 1


def test_capacity_exactly_at_max():
    assert has_available_capacity(10, 10) is False    # current == max


def test_capacity_above_max():
    assert has_available_capacity(11, 10) is False    # current > max


def test_name_exactly_two_characters(sample_participant_dict):
    sample_participant_dict["name"] = "Al"            # minimum allowed
    assert ParticipantCreate(**sample_participant_dict).name == "Al"


def test_capacity_empty_event():
    assert has_available_capacity(0, 1) is True


# ---------- Negative (≥ 2) ----------
@pytest.mark.parametrize("bad_email", ["not-an-email", "missing@domain", "@no-user.com", ""])
def test_invalid_email_rejected(sample_participant_dict, bad_email):
    sample_participant_dict["email"] = bad_email
    with pytest.raises(ValidationError):
        ParticipantCreate(**sample_participant_dict)


def test_short_name_rejected(sample_participant_dict):
    sample_participant_dict["name"] = "A"             # 1 char < 2
    with pytest.raises(ValidationError):
        ParticipantCreate(**sample_participant_dict)


def test_duplicate_registration_raises():
    with pytest.raises(ValueError, match="already registered"):
        check_duplicate_registration([1, 2, 3], 2)