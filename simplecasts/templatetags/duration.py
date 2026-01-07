from datetime import timedelta

from django import template
from django.utils import timezone
from django.utils.timesince import timesince

register = template.Library()


@register.filter
def format_duration(total_seconds: int, min_value: int = 60) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1 hour, 30 minutes."""
    return (
        timesince(timezone.now() - timedelta(seconds=total_seconds))
        if total_seconds >= min_value
        else ""
    )
