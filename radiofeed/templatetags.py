import functools
import json
from datetime import timedelta
from typing import Final

from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.shortcuts import resolve_url
from django.template.context import RequestContext
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince

from radiofeed import pwa
from radiofeed.cover_image import get_cover_image_attrs, get_cover_image_class
from radiofeed.html import render_markdown

_SECONDS_IN_MINUTE: Final = 60
_SECONDS_IN_HOUR: Final = 3600

register = template.Library()

get_cover_image_attrs = register.simple_tag(get_cover_image_attrs)
get_cover_image_class = register.simple_tag(get_cover_image_class)


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
    return format_html('<meta name="theme-color" content="{}">', pwa.get_theme_color())


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


@register.simple_tag(takes_context=True)
def get_accept_cookies(context: RequestContext) -> bool:
    """Returns True if user has accepted cookies."""
    return settings.GDPR_COOKIE_NAME in context.request.COOKIES


@register.filter
def markdown(content: str | None) -> str:
    """Render content as Markdown."""
    return render_markdown(content or "")


@register.filter
def format_duration(total_seconds: int | None, min_seconds: int = 60) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1 hour, 30 minutes."""
    if total_seconds and total_seconds > min_seconds:
        return timesince(timezone.now() - timedelta(seconds=total_seconds))
    return ""
