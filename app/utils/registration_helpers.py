def has_available_capacity(current_count: int, max_capacity: int) -> bool:
    return current_count < max_capacity


def check_duplicate_registration(registered_ids: list[int], new_id: int) -> None:
    if new_id in registered_ids:
        raise ValueError(f"Participant {new_id} is already registered.")