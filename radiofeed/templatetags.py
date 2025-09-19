import functools
import json
from typing import Final

from django import forms, template
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import resolve_url
from django.template.context import Context
from django.template.defaultfilters import pluralize

from radiofeed import pwa
from radiofeed.cover_image import get_cover_image_attrs
from radiofeed.html import render_markdown

_TIME_PARTS: Final = [
    ("hour", 60 * 60),
    ("minute", 60),
]

register = template.Library()

get_cover_image_attrs = register.simple_tag(get_cover_image_attrs)


_jsonify = functools.partial(json.dumps, cls=DjangoJSONEncoder)


@register.simple_tag
def get_meta_config() -> dict:
    """Returns META config settings."""
    return settings.META_CONFIG


@register.simple_tag
def get_htmx_config() -> str:
    """Returns HTMX config in meta tag."""
    return _jsonify(settings.HTMX_CONFIG)


@register.simple_tag
def get_theme_color() -> str:
    """Returns theme color in meta tag."""
    return pwa.get_theme_color()


@register.simple_tag
def absolute_uri(site: Site, path: str, *args, **kwargs) -> str:
    """Returns absolute URI for the given path."""
    scheme = "https" if settings.USE_HTTPS else "http"
    url = resolve_url(path, *args, **kwargs)
    return f"{scheme}://{site.domain}{url}"


@register.simple_tag(takes_context=True)
def get_cookies_accepted(context: Context) -> bool:
    """Returns True if user has accepted cookies."""
    if request := context.get("request", None):
        return settings.GDPR_COOKIE_NAME in request.COOKIES
    return False


@register.filter
def markdown(content: str | None) -> str:
    """Render content as Markdown."""
    return render_markdown(content) if content else ""


@register.filter
def format_duration(total_seconds: int) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1 hour, 30 minutes."""
    parts: list[str] = []
    for label, seconds in _TIME_PARTS:
        value = total_seconds // seconds
        total_seconds -= value * seconds
        if value:
            parts.append(f"{value} {label}{pluralize(value)}")
    return " ".join(parts)


@register.filter
def widget_type(field: forms.Field) -> str:
    """Returns the widget class name for the bound field."""
    return field.field.widget.__class__.__name__.lower()


@register.simple_tag
def render_field(field: forms.Field, **attrs) -> str:
    """Returns rendered widget."""
    attrs = {
        k.replace(
            "_",
            "-",
        ): v
        for k, v in attrs.items()
        if v not in (None, False)
    }
    return field.as_widget(attrs=attrs)
