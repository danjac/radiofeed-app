# Standard Library
import math

# Django
from django import template
from django.template.defaultfilters import stringfilter

# Local
from ..models import Episode

register = template.Library()


@register.simple_tag(takes_context=True)
def is_playing(context, episode):
    player = context["request"].session.get("player")
    if player is None:
        return False
    return player["episode"] == episode.id


@register.simple_tag(takes_context=True)
def get_player(context):
    request = context["request"]
    player = request.session.get("player")
    if player is None:
        return None

    try:
        episode = Episode.objects.select_related("podcast").get(pk=player["episode"])
    except Episode.DoesNotExist:
        return None

    return {"episode": episode, "current_time": player["current_time"]}


@register.filter
@stringfilter
def duration_in_seconds(duration):
    """Returns duration string in h:m:s or h:m to seconds"""
    if not duration:
        return 0
    hours, minutes, seconds = 0, 0, 0
    parts = duration.split(":")
    num_parts = len(parts)

    if num_parts == 1:
        seconds = parts[0]
    elif num_parts == 2:
        [minutes, seconds] = parts
    elif num_parts == 3:
        [hours, minutes, seconds] = parts
    else:
        return 0

    try:
        return (int(hours) * 3600) + (int(minutes) * 60) + int(seconds)
    except ValueError:
        return 0


@register.filter
@stringfilter
def format_duration(duration):
    """Formats duration as human readable value e.g. 1h 30min"""
    if not duration:
        return ""

    total_seconds = duration_in_seconds(duration)

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
