from __future__ import annotations

import dataclasses
import math
import re

from urllib import parse

from django import template
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.template.defaultfilters import stringfilter, urlencode
from django.urls import reverse
from django.utils.safestring import mark_safe

from radiofeed.common.utils.html import markup

register = template.Library()

_validate_url = URLValidator(["http", "https"])


@dataclasses.dataclass
class ActiveLink:
    """Active link info returned from `active_link` or `re_active_link` filters.

    Attributes:
        url: resolved URL
        match: if the URL matches whatever pattern
        exact: if the URL is an exact match
    """

    url: str
    match: bool = False
    exact: bool = False


@dataclasses.dataclass(frozen=True)
class SiteConfig:
    """General site information."""

    contact_email: str
    country: str
    description: str
    keywords: str
    owner: str


@register.simple_tag(takes_context=True)
def pagination_url(context: dict, page_number: int, param: str = "page") -> str:
    """Inserts the "page" query string parameter with the provided page number into the template.

    Preserves the original request path and any other query string parameters.

    Given the above and a URL of "/search?q=test" the result would
    be something like: "/search?q=test&page=3"

    Args:
        context: template context
        page_number
        param: query string parameter for pages

    Returns:
        updated URL path with new page
    """
    request = context["request"]
    params = request.GET.copy()
    params[param] = page_number
    return request.path + "?" + params.urlencode()


@register.simple_tag
def get_site_config() -> SiteConfig:
    """Returns the configuration defined in the setting SITE_CONFIG."""
    return SiteConfig(**settings.SITE_CONFIG)


@register.simple_tag(takes_context=True)
def absolute_uri(context: dict, url: str | None = None, *args, **kwargs) -> str:
    """Generate absolute URI based on server environment or current Site.

    Args:
        context: template context
        url: URL name or path
    """
    return _build_absolute_uri(
        resolve_url(url, *args, **kwargs) if url else None, context.get("request")
    )


@register.filter
def format_duration(total_seconds: int | None) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1h 30min."""
    if total_seconds is None or total_seconds < 60:
        return ""

    rv = []

    if total_hours := math.floor(total_seconds / 3600):
        rv.append(f"{total_hours}h")

    if total_minutes := round((total_seconds % 3600) / 60):
        rv.append(f"{total_minutes}min")

    return " ".join(rv)


@register.simple_tag(takes_context=True)
def active_link(context: dict, url_name: str, *args, **kwargs) -> ActiveLink:
    """Returns url with active link info."""
    url = resolve_url(url_name, *args, **kwargs)

    if context["request"].path == url:
        return ActiveLink(url, match=True, exact=True)

    if context["request"].path.startswith(url):
        return ActiveLink(url, match=True)

    return ActiveLink(url)


@register.simple_tag(takes_context=True)
def re_active_link(
    context: dict,
    url_name: str,
    pattern: str,
    *args,
    **kwargs,
) -> ActiveLink:
    """Returns url with active link info."""
    url = resolve_url(url_name, *args, **kwargs)
    if re.match(pattern, context["request"].path):
        return ActiveLink(url, match=True)

    return ActiveLink(url)


@register.filter
def login_url(url: str) -> str:
    """Returns login URL with redirect parameter back to this url."""
    return _auth_redirect_url(url, reverse("account_login"))


@register.filter
def signup_url(url: str) -> str:
    """Returns signup URL with redirect parameter back to this url."""
    return _auth_redirect_url(url, reverse("account_signup"))


@register.inclusion_tag("includes/markdown.html")
def markdown(value: str | None) -> dict:
    """Renders markdown content."""
    return {"content": mark_safe(markup(value))}  # nosec


@register.inclusion_tag("includes/share_buttons.html", takes_context=True)
def share_buttons(
    context: dict, url: str, subject: str, extra_context: dict | None = None
) -> dict:
    """Render set of share buttons for a page for email, Facebook, Twitter and Linkedin.

    Args:
        context: template context
        url: URL on page to share in link (automatically expanded to absolute URI)
        subject: subject line
        extra_context: extra template context
    """
    url = parse.quote(context["request"].build_absolute_uri(url))
    subject = parse.quote(subject)

    return {
        "share_urls": {
            "email": f"mailto:?subject={subject}&body={url}",
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={url}",
            "twitter": f"https://twitter.com/share?url={url}&text={subject}",
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={url}",
        },
    } | (extra_context or {})


@register.inclusion_tag("includes/cookie_notice.html", takes_context=True)
def cookie_notice(context: dict) -> dict:
    """Renders GDPR cookie notice. Notice should be hidden once user has clicked "Accept Cookies" button."""
    return {"accept_cookies": "accept-cookies" in context["request"].COOKIES}


@register.filter
@stringfilter
def normalize_url(url: str) -> str:
    """If a URL is provided minus http(s):// prefix, prepends protocol."""
    if url:
        for value in (url, "https://" + url):
            try:
                _validate_url(value)
                return value
            except ValidationError:
                continue
    return ""


def _auth_redirect_url(url: str, redirect_url) -> str:
    return (
        redirect_url
        if url.startswith("/account/")
        else f"{redirect_url}?{REDIRECT_FIELD_NAME}={urlencode(url)}"
    )


def _build_absolute_uri(url: str | None = None, request: HttpRequest | None = None):
    if request:
        return request.build_absolute_uri(url)

    # in case we don't have a request, e.g. in email job
    domain = Site.objects.get_current().domain
    protocol = "https" if settings.SECURE_SSL_REDIRECT else "http"
    base_url = protocol + "://" + domain

    return parse.urljoin(base_url, url) if url else base_url
