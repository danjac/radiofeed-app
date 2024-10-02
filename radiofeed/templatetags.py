import functools
import json
import math
from typing import Final

from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.shortcuts import resolve_url
from django.template.context import RequestContext
from django.template.defaultfilters import pluralize
from django.utils.html import format_html

from radiofeed.cover_image import (
    CoverImageVariant,
    get_cover_image_attrs,
    get_cover_image_class,
)
from radiofeed.html import render_markdown
from radiofeed.manifest import get_theme_color

_SECONDS_IN_MINUTE: Final = 60
_SECONDS_IN_HOUR: Final = 3600

register = template.Library()

get_cover_image_attrs = register.simple_tag(get_cover_image_attrs)


@register.simple_tag
def htmx_config() -> str:
    """Returns HTMX config in meta tag."""
    return format_html(
        '<meta name="htmx-config" content="{}">',
        json.dumps(settings.HTMX_CONFIG, cls=DjangoJSONEncoder),
    )


@register.simple_tag
def theme_color() -> str:
    """Returns the PWA configuration theme color meta tag."""
    return format_html('<meta name="theme-color" content="{}">', get_theme_color())


@register.simple_tag
@functools.cache
def get_site() -> Site:
    """Returns the current Site instance. Use when `request.site` is unavailable, e.g. in emails run from cronjobs."""

    return Site.objects.get_current()


@register.simple_tag
def absolute_uri(url: Model | str | None = None, *url_args, **url_kwargs) -> str:
    """Returns the absolute URL to site domain."""

    site = get_site()
    path = resolve_url(url, *url_args, **url_kwargs) if url else ""
    scheme = "https" if settings.SECURE_SSL_REDIRECT else "http"

    return f"{scheme}://{site.domain}{path}"


@register.inclusion_tag("_cover_image.html")
def cover_image(
    variant: CoverImageVariant,
    cover_url: str | None,
    title: str,
    **attrs: str,
) -> dict:
    """Renders a cover image with proxy URL."""
    return {
        "class": get_cover_image_class(variant, attrs.pop("class", "")),
        "attrs": get_cover_image_attrs(variant, cover_url, title, **attrs),
    }


@register.inclusion_tag("_gdpr_cookies_banner.html", takes_context=True)
def gdpr_cookies_banner(context: RequestContext) -> dict:
    """Renders GDPR cookie notice. Notice should be hidden once user has clicked
    "Accept Cookies" button."""
    return {
        "accept_cookies": settings.GDPR_COOKIE_NAME in context.request.COOKIES,
    }


@register.inclusion_tag("_markdown.html")
def markdown(content: str | None) -> dict:
    """Render content as Markdown."""
    return {"content": render_markdown(content or "")}


@register.filter
def format_duration(total_seconds: int | None) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1h 30min."""
    if total_seconds is None or total_seconds < _SECONDS_IN_MINUTE:
        return ""

    rv: list[str] = []

    if total_hours := math.floor(total_seconds / _SECONDS_IN_HOUR):
        rv.append(f"{total_hours} hour{pluralize(total_hours)}")

    if total_minutes := round((total_seconds % _SECONDS_IN_HOUR) / _SECONDS_IN_MINUTE):
        rv.append(f"{total_minutes} minute{pluralize(total_minutes)}")

    return " ".join(rv)


@register.filter
def percentage(value: float, total: float) -> int:
    """Returns % value.

    Example:
    {{ value|percentage:total }}% done
    """
    if 0 in (value, total):
        return 0
    return min(math.ceil((value / total) * 100), 100)
