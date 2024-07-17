from __future__ import annotations

import functools
import math
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Final, TypedDict

from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.paginator import Page
from django.shortcuts import resolve_url
from django.template.defaultfilters import pluralize
from django.utils.safestring import mark_safe

from radiofeed import cover_image, markdown, pagination

if TYPE_CHECKING:  # pragma: nocover
    from django.core.paginator import Page
    from django.db.models import QuerySet
    from django.template.context import RequestContext

    from radiofeed.cover_image import CoverImageVariant

ACCEPT_COOKIES_NAME: Final = "accept-cookies"


_SECONDS_IN_MINUTE: Final = 60
_SECONDS_IN_HOUR: Final = 3600

register = template.Library()


class ActiveLink(TypedDict):
    """Provides details on whether a link is currently active, along with its
    URL and CSS."""

    url: str
    css: str
    active: bool


@register.simple_tag(takes_context=True)
def active_link(
    context: RequestContext,
    to: Any,
    *,
    css: str = "link",
    active_css: str = "active",
    **kwargs,
) -> ActiveLink:
    """Returns url with active link info if matching URL."""
    url = resolve_url(to, **kwargs)
    return (
        ActiveLink(active=True, css=f"{css} {active_css}", url=url)
        if context.request.path == url
        else ActiveLink(active=False, css=css, url=url)
    )


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
    return math.ceil((value / total) * 100)


@register.simple_tag(takes_context=True)
def paginate(
    context: RequestContext,
    object_list: QuerySet,
    **kwargs,
) -> Page:
    """Returns paginated object list."""

    return pagination.paginate(context.request, object_list, **kwargs)


@register.simple_tag(takes_context=True)
def query_string(context: RequestContext, **kwargs) -> str:
    """Replace values with query string values.

    If value is None, then removes that param.

    This can be replaced with Django 5.1 upgrade, which has a more complete implementation.
    """
    dct = context.request.GET.copy()
    for param, value in kwargs.items():
        if value is None:
            if param in dct:
                del dct[param]
        elif isinstance(value, Iterable) and not isinstance(value, str):
            dct.setlist(param, value)
        else:
            dct[param] = value
    if dct:
        return f"?{dct.urlencode()}"
    return ""


@register.simple_tag
@functools.cache
def get_site() -> Site:
    """Returns the current Site instance. Use when `request.site` is unavailable, e.g. in emails run from cronjobs."""

    return Site.objects.get_current()


@register.simple_tag
def absolute_uri(to: Any | None = None, *args, **kwargs) -> str:
    """Returns the absolute URL to site domain."""

    site = get_site()
    path = resolve_url(to, *args, **kwargs) if to else ""
    scheme = "https" if settings.SECURE_SSL_REDIRECT else "http"

    return f"{scheme}://{site.domain}{path}"


@register.inclusion_tag("_markdown.html", name="markdown")
def render_markdown(value: str | None) -> dict:
    """Renders cleaned HTML/Markdown content."""
    return {"content": mark_safe(markdown.render(value or ""))}  # noqa: S308


@register.inclusion_tag("_cookie_notice.html", name="cookie_notice", takes_context=True)
def render_cookie_notice(context: RequestContext) -> dict:
    """Renders GDPR cookie notice. Notice should be hidden once user has clicked
    "Accept Cookies" button."""
    return {"accept_cookies": ACCEPT_COOKIES_NAME in context.request.COOKIES}


@register.inclusion_tag("_cover_image.html", name="cover_image")
def render_cover_image(
    cover_url: str | None,
    variant: CoverImageVariant,
    title: str,
    *,
    url: str = "",
    css_class: str = "",
) -> dict:
    """Renders a cover image with proxy URL."""
    return {
        "cover_url": cover_url,
        "css_class": css_class,
        "variant": variant,
        "title": title,
        "url": url,
    }


get_cover_image_attrs = register.simple_tag(cover_image.get_cover_image_attrs)
