from typing import Optional, Union

from django import template
from django.template.context import Context

from .. import utils
from ..player import PlayerInfo

register = template.Library()


@register.simple_tag(takes_context=True)
def get_player(context: Context) -> PlayerInfo:
    return context["request"].player.as_dict()


@register.filter
def format_duration(total_seconds: Optional[int]) -> Union[str, int]:
    try:
        return utils.format_duration(int(total_seconds or 0))
    except ValueError:
        return 0
