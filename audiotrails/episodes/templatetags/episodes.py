from django import template

from .. import utils

register = template.Library()


@register.simple_tag(takes_context=True)
def get_player(context):
    return context["request"].player.as_dict()


@register.filter
def format_duration(total_seconds):
    try:
        return utils.format_duration(int(total_seconds or 0))
    except ValueError:
        return 0
