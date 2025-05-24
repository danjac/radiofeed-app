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
from django.template.context import Context
from django.template.defaultfilters import pluralize

from radiofeed import pwa
from radiofeed.cover_image import (
    CoverImageVariant,
    get_cover_image_attrs,
    get_cover_image_class,
)
from radiofeed.html import render_markdown

_TIME_PARTS: Final = [
    ("hour", 60 * 60),
    ("minute", 60),
]

register = template.Library()

get_cover_image_attrs = register.simple_tag(get_cover_image_attrs)
get_cover_image_class = register.simple_tag(get_cover_image_class)


_jsonify = functools.partial(json.dumps, cls=DjangoJSONEncoder)


@register.simple_tag
def htmx_config() -> str:
    """Returns HTMX config in meta tag."""
    return _jsonify(settings.HTMX_CONFIG)


@register.simple_tag
def theme_color() -> str:
    """Returns theme color in meta tag."""
    return pwa.get_theme_color()


@register.simple_tag
@functools.cache
def get_site() -> Site:
    """Returns the current Site instance. Use when `request.site` is unavailable, e.g. in emails run from cronjobs."""

    return Site.objects.get_current()


@register.simple_tag
def absolute_uri(url: Model | str | None = None, *url_args, **url_kwargs) -> str:
    """Returns the absolute URL to site domain. Use this if request is unavailable."""
    path = resolve_url(url, *url_args, **url_kwargs) if url else ""
    scheme = "https" if settings.USE_HTTPS else "http"
    return f"{scheme}://{get_site().domain}{path}"


@register.simple_tag(takes_context=True)
def csrf_header(context: Context, **kwargs) -> str:
    """Returns CSRF token header in JSON format.
    Additional arbitrary arguments also can be passed to the JSON object.
    """
    if request := context.get("request", None):
        kwargs |= {_csrf_header_name(): get_token(request)}
    return _jsonify(kwargs)


@register.inclusion_tag("cookie_banner.html", takes_context=True)
def cookie_banner(context: Context) -> dict:
    """Returns True if user has accepted cookies."""
    cookies_accepted = False
    if request := context.get("request", None):
        cookies_accepted = settings.GDPR_COOKIE_NAME in request.COOKIES
    return {
        "cookies_accepted": cookies_accepted,
        "request": request,
    }


@register.inclusion_tag("cover_image.html")
def cover_image(
    variant: CoverImageVariant,
    cover_url: str | None,
    title: str,
    **attrs,
) -> dict:
    """Renders a cover image."""
    return {
        "attrs": get_cover_image_attrs(
            variant,
            cover_url,
            title,
            **attrs,
        ),
    }


@register.inclusion_tag("markdown.html")
def markdown(content: str | None) -> dict:
    """Render content as Markdown."""
    content = render_markdown(content) if content else ""
    return {"content": content}


@register.simple_block_tag(takes_context=True)
def fragment(
    context: Context,
    content: str,
    template_name: str,
    **extra_context,
) -> str:
    """Renders a block fragment."""
    template = context.template.engine.get_template(template_name)  # type: ignore[reportOptionalMemberAccess]
    with context.push(content=content, **extra_context):
        return template.render(context)


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
