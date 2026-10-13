def filter_events_by_location(events: list[dict], location: str) -> list[dict]:
    """Filter events by location, ignoring uppercase/lowercase differences."""
    return [
        event for event in events
        if location.lower() in event["location"].lower()
    ]


def filter_events_by_title(events: list[dict], title: str) -> list[dict]:
    """Filter events by title, ignoring uppercase/lowercase differences."""
    return [
        event for event in events
        if title.lower() in event["title"].lower()
    ]