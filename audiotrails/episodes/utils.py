import math


def format_duration(total_seconds):
    """Formats duration (in seconds) as human readable value e.g. 1h 30min"""
    if not total_seconds:
        return ""

    rv = []

    if total_hours := math.floor(total_seconds / 3600):
        rv.append(f"{total_hours}h")

    if total_minutes := round((total_seconds % 3600) / 60):
        rv.append(f"{total_minutes}min")

    return " ".join(rv) if rv else "<1min"


def duration_in_seconds(duration):
    """Returns total number of seconds given string in [h:][m:]s format.
    Invalid formats return zero."""

    if not duration:
        return 0

    try:
        return sum(
            (int(part) * multiplier)
            for (part, multiplier) in zip(
                reversed(duration.split(":")[:3]), (1, 60, 3600)
            )
        )
    except ValueError:
        return 0
