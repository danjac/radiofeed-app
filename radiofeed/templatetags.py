import functools
import json
import math
from typing import Final, TypeAlias, TypedDict

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

URL: TypeAlias = Model | str


class ActiveLink(TypedDict):
    """Provides details on whether a link is currently active, along with its
    URL and CSS."""

    url: str
    css: str
    active: bool


@register.simple_tag(takes_context=True)
def active_link(
    context: RequestContext,
    url: URL,
    *url_args,
    css: str = "link",
    active_css: str = "active",
    **url_kwargs,
) -> ActiveLink:
    """Returns url with active link info if matching URL."""
    url = resolve_url(url, *url_args, **url_kwargs)
    return (
        ActiveLink(active=True, css=f"{css} {active_css}", url=url)
        if context.request.path == url
        else ActiveLink(active=False, css=css, url=url)
    )


@register.simple_tag(takes_context=True)
def json_data(
    context: RequestContext,
    dct: dict | None = None,
    *,
    csrf: bool = False,
    **data,
) -> str:
    """Renders JSON strig suitable for attributes such as hx-headers or hx-vals that expect a JSON value.

    If `csrf` is `True` will include the `X-CSRFToken` header with current csrf_token. For example:

        hx-headers="{% json_data crsf=True %}"

    will render something like:

        hx-headers="&quot;X-CSRFToken&quot;=&quot;...&quot;"
    """

    dct = (dct or {}) | data

    if csrf and (token := context.get("csrf_token")):
        dct["X-CSRFToken"] = str(token)

    return format_html("{}", json.dumps(dct, cls=DjangoJSONEncoder))


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
def absolute_uri(url: URL | None = None, *url_args, **url_kwargs) -> str:
    """Returns the absolute URL to site domain."""

    site = get_site()
    path = resolve_url(url, *url_args, **url_kwargs) if url else ""
    scheme = "https" if settings.SECURE_SSL_REDIRECT else "http"

    return f"{scheme}://{site.domain}{path}"


@register.inclusion_tag("_cover_image.html")
def cover_image(
    variant: CoverImageVariant,
    cover_url: str,
    title: str,
    *,
    css_class: str = "",
) -> dict:
    """Renders a cover image with proxy URL."""
    return {
        "attrs": get_cover_image_attrs(variant, cover_url)
        | {
            "alt": title,
            "title": title,
        },
        "class": get_cover_image_class(variant, css_class),
    }


@register.inclusion_tag("_gdpr_cookies_banner.html", takes_context=True)
def gdpr_cookies_banner(context: RequestContext) -> dict:
    """Renders GDPR cookie notice. Notice should be hidden once user has clicked
    "Accept Cookies" button."""
    return {
        "accept_cookies": settings.GDPR_COOKIE_NAME in context.request.COOKIES,
    }


@register.inclusion_tag("_search_form.html", takes_context=True)
def search_form(
    context: RequestContext,
    placeholder: str = "Search",
    url: URL | None = None,
    *url_args,
    clear_search: bool = True,
    **url_kwargs,
):
    """Renders a search form.

    If `clear_search` is `True`, clicking the "clear search" button reloads the current page.

    If `False` the user can clear the input field but the page is not reloaded.

    Assumes current URL unless `to` is passed in.
    """

    search_url = (
        resolve_url(url, *url_args, **url_kwargs) if url else context.request.path
    )

    return {
        "request": context.request,
        "placeholder": placeholder,
        "search_url": search_url,
        "clear_search": clear_search,
    }


@register.inclusion_tag("_search_form.html#button", takes_context=True)
def search_button(
    context: RequestContext,
    text: str,
    url: URL,
    *url_args,
    **url_kwargs,
):
    """Renders a search button.

    This button redirects search to another page specified in {% search_form %}.
    """

    return {
        "request": context.request,
        "text": text,
        "search_url": resolve_url(url, *url_args, **url_kwargs),
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
