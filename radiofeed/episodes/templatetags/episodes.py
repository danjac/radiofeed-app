# Standard Library
import math

# Django
from django import template

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
