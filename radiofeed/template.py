from __future__ import annotations

import math
import urllib.parse

from django import template
from django.core.exceptions import ValidationError
from django.core.signing import Signer
from django.core.validators import URLValidator
from django.shortcuts import resolve_url
from django.template.context import RequestContext
from django.template.defaultfilters import stringfilter
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe

from radiofeed import cleaners

register = template.Library()

_validate_url = URLValidator(["http", "https"])


@register.simple_tag(takes_context=True)
def pagination_url(context: RequestContext, page_number: int) -> str:
    """Inserts the "page" query string parameter with the provided page number into the template.

    Preserves the original request path and any other query string parameters.

    Given the above and a URL of "/search?q=test" the result would
    be something like: "/search?q=test&page=3"

    Requires `PaginationMiddleware` in MIDDLEWARE.

    Returns:
        updated URL path with new page
    """
    return context.request.pagination.url(page_number)


@register.simple_tag(takes_context=True)
def active_link(
    context: RequestContext,
    url_name: str,
    css: str = "link",
    active_css: str = "active",
    *args,
    **kwargs,
) -> dict:
    """Returns url with active link info."""
    url = resolve_url(url_name, *args, **kwargs)
    dct = {"active": False, "css": css, "url": url}

    return (
        {**dct, "active": True, "css": f"{css} {active_css}"}
        if context.request.path == url
        else dct
    )


@register.inclusion_tag("includes/html_content.html")
def render_html(value: str | None) -> dict:
    """Renders cleaned HTML content."""
    return {"content": mark_safe(cleaners.clean_html(value or ""))}  # nosec


@register.inclusion_tag("includes/cookie_notice.html", takes_context=True)
def cookie_notice(context: RequestContext) -> dict:
    """Renders GDPR cookie notice. Notice should be hidden once user has clicked "Accept Cookies" button."""
    return {"accept_cookies": "accept-cookies" in context.request.COOKIES}


@register.simple_tag
def cover_image_url(cover_url: str, size: int) -> str:
    """Returns signed cover image URL."""
    return (
        reverse(
            "cover_image",
            kwargs={
                "size": size,
            },
        )
        + "?"
        + urllib.parse.urlencode({"url": Signer().sign(cover_url)})
        if cover_url
        else ""
    )


@register.inclusion_tag("includes/cover_image.html")
def cover_image(
    cover_url: str,
    size: int,
    title: str,
    url: str = "",
    css_class: str = "",
) -> dict:
    """Renders a cover image with proxy URL."""
    placeholder = static(f"img/placeholder-{size}.webp")

    return {
        "cover_url": cover_image_url(cover_url, size),
        "placeholder": placeholder,
        "title": title,
        "size": size,
        "url": url,
        "css_class": css_class,
    }


@register.filter
def format_duration(total_seconds: int | None) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1h 30min."""
    if total_seconds is None or total_seconds < 60:
        return ""

    rv: list[str] = []

    if total_hours := math.floor(total_seconds / 3600):
        rv.append(f"{total_hours}h")

    if total_minutes := round((total_seconds % 3600) / 60):
        rv.append(f"{total_minutes}min")

    return " ".join(rv)


@register.filter
@stringfilter
def force_url(url: str) -> str:
    """If a URL is provided minus http(s):// prefix, prepends protocol.

    If we cannot create a valid URL, just return an empty string.
    """
    if url:
        for value in (url, f"https://{url}"):
            try:
                _validate_url(value)
                return value
            except ValidationError:
                continue
    return ""
