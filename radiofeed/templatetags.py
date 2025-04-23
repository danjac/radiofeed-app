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
from django.template.context import RequestContext
from django.template.defaultfilters import pluralize
from django.utils.html import format_html_join

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


@register.simple_tag
def absolute_uri(url: Model | str | None = None, *url_args, **url_kwargs) -> str:
    """Returns the absolute URL to site domain. Use this if request is unavailable."""
    path = resolve_url(url, *url_args, **url_kwargs) if url else ""
    scheme = "https" if settings.USE_HTTPS else "http"
    return f"{scheme}://{get_site().domain}{path}"


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


@register.simple_block_tag(takes_context=True)
def deferred(
    context: RequestContext,
    content: str,
    group: str,
    content_id: str,
) -> str:
    """Instead of rendering the content immediately, render using the `render_deferred` tag.
    This is useful for rendering content we don't want to include immediately e.g. JS or CSS tags.

    Use with DeferredHTMLMiddleware.

    Example:
        {% deferred "js" "example1" %}
        <script src="https://example.com/script1.js"></script>
        {% enddeferred %}

        {% deferred "js" "example2" %}
        <script src="https://example.com/script2.js"></script>
        {% enddeferred %}

        {% deferred "js" "example1" %}
        <script src="https://example.com/script1.js"></script>
        {% enddeferred %}
    at end of page:
        {% render_deferred "js" %}

    This will render all content in group "js". "example1" and "example2" will just be rendered once:

        <script src="https://example.com/script1.js"></script>
        <script src="https://example.com/script2.js"></script>
    """
    context.request.deferred_html[group][content_id] = content
    return ""


@register.simple_tag(takes_context=True)
def render_deferred(context: RequestContext, group: str, joiner: str = "") -> str:
    """Renders all deferred content for a group, cleares the list and returns the result."""
    if deferred_html := context.request.deferred_html.pop(group, None):
        return format_html_join(
            joiner,
            "{}",
            ((block,) for block in deferred_html.values()),
        )
    return ""


@functools.cache
def _csrf_header_name() -> str:
    return settings.CSRF_HEADER_NAME.replace("HTTP_", "", 1).replace("_", "-")
