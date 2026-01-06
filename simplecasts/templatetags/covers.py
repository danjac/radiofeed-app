import functools

from django import template
from django.forms.utils import flatatt
from django.utils.html import format_html

from simplecasts.services import covers

register = template.Library()


@register.simple_tag
@functools.cache
def get_cover_image_attrs(
    variant: covers.CoverVariant,
    cover_url: str,
    title: str,
) -> dict:
    """Returns cover image attributes."""
    return covers.get_cover_image_attrs(variant, cover_url, title)


@register.simple_tag
@functools.cache
def cover_image(
    variant: covers.CoverVariant,
    cover_url: str,
    title: str,
) -> str:
    """Renders a cover image."""
    attrs = get_cover_image_attrs(variant, cover_url, title)
    return format_html("<img {}>", flatatt(_clean_attrs(attrs)))


def _clean_attrs(attrs: dict) -> dict:
    return {k.replace("_", "-"): v for k, v in attrs.items() if v not in (None, False)}
