import math


def format_duration(total_seconds):
    """Formats duration (in seconds) as human readable value e.g. 1h 30min"""
    if not total_seconds:
        return ""

    total_hours = math.floor(total_seconds / 3600)
    total_minutes = round((total_seconds % 3600) / 60)

    if not total_minutes and not total_hours:
        return "<1min"

    rv = []
    if total_hours:
        rv.append(f"{total_hours}h")
    if total_minutes:
        rv.append(f"{total_minutes}min")
    return " ".join(rv)
