
def has_available_capacity(current_count: int, max_capacity: int) -> bool:
    """Return True if the event has at least one available place."""
    return current_count < max_capacity


def check_duplicate_registration(registered_ids: list[int], new_id: int) -> None:
    """Raise ValueError if the participant is already registered."""
    if new_id in registered_ids:
        raise ValueError("Participant is already registered.")