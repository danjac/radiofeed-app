import functools
import math
import urllib.parse
from typing import Any, TypedDict

from django import template
from django.contrib.sites.models import Site
from django.core.signing import Signer
from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe

from radiofeed import cleaners

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
    css: str = "link",
    active_css: str = "active",
    *args,
    **kwargs,
) -> ActiveLink:
    """Returns url with active link info."""
    url = resolve_url(to, *args, **kwargs)

    return (
        ActiveLink(active=True, css=f"{css} {active_css}", url=url)
        if context.request.path == url
        else ActiveLink(active=False, css=css, url=url)
    )


@register.inclusion_tag("_markdown.html")
def markdown(value: str | None) -> dict:
    """Renders cleaned HTML/Markdown content."""
    return {"content": mark_safe(cleaners.clean_html(value or ""))}  # noqa


@register.inclusion_tag("_cookie_notice.html", takes_context=True)
def cookie_notice(context: RequestContext) -> dict:
    """Renders GDPR cookie notice. Notice should be hidden once user has clicked
    "Accept Cookies" button."""
    return {"accept_cookies": "accept-cookies" in context.request.COOKIES}


@register.simple_tag
@functools.cache
def get_cover_image_url(cover_url: str | None, size: int) -> str:
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


@register.simple_tag
@functools.cache
def get_placeholder_cover_url(size: int) -> str:
    """Return placeholder cover image URL."""

    return static(f"img/placeholder-{size}.webp")


@register.inclusion_tag("_cover_image.html")
@functools.cache
def cover_image(
    cover_url: str | None,
    size: int,
    title: str,
    url: str = "",
    css_class: str = "",
) -> dict:
    """Renders a cover image with proxy URL."""

    return {
        "cover_url": get_cover_image_url(cover_url, size),
        "placeholder": get_placeholder_cover_url(size),
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


@register.simple_tag(takes_context=True)
def pagination_url(context: RequestContext, page_number: int) -> str:
    """Returns URL for next/previous page."""
    return context.request.pagination.url(page_number)


@register.simple_tag(takes_context=True)
def render(context: RequestContext, template_name: str, **extra_context) -> str:
    """Renders template contents into string."""
    return render_to_string(
        template_name,
        {
            **context.flatten(),
            **extra_context,
        },
        request=context.request,
    )


@register.simple_tag
def absolute_uri(to: Any, *args, **kwargs) -> str:
    """Return absolute URL. Use outside of HTTP request scope, e.g. in email links."""
    request = HttpRequest()
    request.META = {"HTTP_HOST": get_site().domain}
    return request.build_absolute_uri(resolve_url(to, *args, **kwargs))


@register.simple_tag
@functools.cache
def get_site() -> Site:
    """Return current site, use when `request.site` is unavailable to template."""
    return Site.objects.get_current()
