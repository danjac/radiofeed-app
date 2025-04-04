import functools
import json
from typing import Final

from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.middleware.csrf import get_token
from django.shortcuts import resolve_url
from django.template.context import Context, RequestContext
from django.template.defaultfilters import pluralize

from radiofeed import pwa
from radiofeed.cover_image import get_cover_image_attrs, get_cover_image_class
from radiofeed.html import render_markdown

_TIME_PARTS: Final = [
    ("hour", 60 * 60),
    ("minute", 60),
]

register = template.Library()

get_cover_image_attrs = register.simple_tag(get_cover_image_attrs)
get_cover_image_class = register.simple_tag(get_cover_image_class)


@register.simple_tag
def htmx_config() -> str:
    """Returns HTMX config in meta tag."""
    return json.dumps(settings.HTMX_CONFIG, cls=DjangoJSONEncoder)


@register.simple_tag
def theme_color() -> str:
    """Returns theme color in meta tag."""
    return pwa.get_theme_color()


@register.simple_tag
@functools.cache
def get_site() -> Site:
    """Returns the current Site instance. Use when `request.site` is unavailable, e.g. in emails run from cronjobs."""

    return Site.objects.get_current()


@register.simple_tag(takes_context=True)
def absolute_uri(
    context: Context, url: Model | str | None = None, *url_args, **url_kwargs
) -> str:
    """Returns the absolute URL to site domain.
    If `request` is available in context, it will be used to build the URL. Otherwise will use the current site domain.
    """

    site = get_site()
    path = resolve_url(url, *url_args, **url_kwargs) if url else ""
    if request := context.get("request"):
        return request.build_absolute_uri(path)
    scheme = "https" if settings.USE_HTTPS else "http"
    return f"{scheme}://{site.domain}{path}"


@register.simple_tag(takes_context=True)
def get_accept_cookies(context: RequestContext) -> bool:
    """Returns True if user has accepted cookies."""
    return settings.GDPR_COOKIE_NAME in context.request.COOKIES


@register.simple_tag(takes_context=True)
def csrf_header(context: RequestContext, **kwargs) -> str:
    """Returns CSRF token header in JSON format.
    Additional arbitrary arguments also can be passed to the JSON object.
    """
    return json.dumps(
        {
            _csrf_header_name(): get_token(context.request),
        }
        | kwargs,
        cls=DjangoJSONEncoder,
    )


@register.filter
def markdown(content: str | None) -> str:
    """Render content as Markdown."""
    return render_markdown(content or "")


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


@functools.cache
def _csrf_header_name() -> str:
    return settings.CSRF_HEADER_NAME.replace("HTTP_", "", 1).replace("_", "-")
