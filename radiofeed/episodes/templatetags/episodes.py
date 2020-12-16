# Django
from django import template

# Local
from .. import utils
from ..models import Episode

register = template.Library()


@register.filter
def subtract(value_a, value_b):
    # should be in common template tags: keeping here for now
    return value_a - value_b


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

    return {
        "episode": episode,
        "current_time": player["current_time"],
        "paused": player.get("paused", False),
    }


@register.filter
def format_duration(total_seconds):
    try:
        return utils.format_duration(int(total_seconds or 0))
    except ValueError:
        return 0
