from typing import Optional, Union

from django import template

from .. import utils

register = template.Library()


@register.filter
def format_duration(total_seconds: Optional[int]) -> Union[str, int]:
    try:
        return utils.format_duration(int(total_seconds or 0))
    except ValueError:
        return 0
