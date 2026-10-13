"""Pure helper functions for searching events (no DB, no HTTP)."""


def filter_events_by_location(events: list[dict], location: str) -> list[dict]:
    """Return events whose location contains `location` (case-insensitive)."""
    needle = location.strip().lower()
    return [e for e in events if needle in e["location"].lower()]


def filter_events_by_title(events: list[dict], title: str) -> list[dict]:
    """Return events whose title contains `title` (case-insensitive)."""
    needle = title.strip().lower()
    return [e for e in events if needle in e["title"].lower()]