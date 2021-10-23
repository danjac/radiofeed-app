from __future__ import annotations

import collections
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

from jcasts.shared import cleaners

register = template.Library()


ActiveLink = collections.namedtuple("ActiveLink", "url match exact")

_validate_url = URLValidator(["http", "https"])


HTTPS_SCHEME = "https://"


@register.simple_tag(takes_context=True)
def pagination_url(context: dict, page_number: int, param: str = "page") -> str:
    """
    Inserts the "page" query string parameter with the
    provided page number into the template, preserving the original
    request path and any other query string parameters.

    Given the above and a URL of "/search?q=test" the result would
    be something like:

    "/search?q=test&page=3"
    """
    request = context["request"]
    params = request.GET.copy()
    params[param] = page_number
    return request.path + "?" + params.urlencode()


@register.simple_tag(takes_context=True)
def absolute_uri(context: dict, url: str | None = None, *args, **kwargs) -> str:
    return build_absolute_uri(
        resolve_url(url, *args, **kwargs) if url else None, context.get("request")
    )


@register.filter
def format_duration(total_seconds: int | None) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1h 30min"""
    if not total_seconds:
        return ""

    rv = []

    if total_hours := math.floor(total_seconds / 3600):
        rv.append(f"{total_hours}h")

    if total_minutes := round((total_seconds % 3600) / 60):
        rv.append(f"{total_minutes}min")

    return " ".join(rv) if rv else "<1min"


@register.simple_tag(takes_context=True)
def active_link(context: dict, url_name: str, *args, **kwargs) -> ActiveLink:
    url = resolve_url(url_name, *args, **kwargs)

    if context["request"].path == url:
        return ActiveLink(url, True, True)

    if context["request"].path.startswith(url):
        return ActiveLink(url, True, False)

    return ActiveLink(url, False, False)


@register.simple_tag(takes_context=True)
def re_active_link(
    context: dict, url_name: str, pattern: str, *args, **kwargs
) -> ActiveLink:
    url = resolve_url(url_name, *args, **kwargs)
    if re.match(pattern, context["request"].path):
        return ActiveLink(url, True, False)

    return ActiveLink(url, False, False)


@register.simple_tag
def get_contact_details() -> dict:
    return settings.CONTACT_DETAILS


@register.filter(is_safe=True)
@stringfilter
def markup(value: str | None) -> str:
    return mark_safe(cleaners.markup(value))  # nosec


@register.filter
def login_url(url: str) -> str:
    return auth_redirect_url(url, reverse("account_login"))


@register.filter
def signup_url(url: str) -> str:
    return auth_redirect_url(url, reverse("account_signup"))


@register.inclusion_tag("icons/_svg.html")
def icon(name: str, css_class: str = "", title: str = "", **attrs) -> dict:
    return {
        "name": name,
        "css_class": css_class,
        "title": title,
        "attrs": attrs,
        "svg_template": f"icons/_{name}.svg",
    }


@register.inclusion_tag("_share_buttons.html", takes_context=True)
def share_buttons(context: dict, url: str, subject: str, css_class: str = "") -> dict:
    url = parse.quote(context["request"].build_absolute_uri(url))
    subject = parse.quote(subject)

    return {
        "css_class": css_class,
        "share_urls": {
            "email": f"mailto:?subject={subject}&body={url}",
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={url}",
            "twitter": f"https://twitter.com/share?url={url}&text={subject}",
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={url}",
        },
    }


@register.inclusion_tag("_cookie_notice.html", takes_context=True)
def cookie_notice(context: dict) -> dict:
    return {"accept_cookies": "accept-cookies" in context["request"].COOKIES}


@register.filter
@stringfilter
def normalize_url(url: str | None) -> str:
    """If a URL is provided minus http(s):// prefix, prepends protocol."""
    if not url:
        return ""
    for value in (url, HTTPS_SCHEME + url):
        try:
            _validate_url(value)
            return value
        except ValidationError:
            pass
    return ""


@register.filter
def safe_url(url: str | None) -> str | None:
    if not url or url.startswith(HTTPS_SCHEME):
        return url
    if url.startswith("http://"):
        return HTTPS_SCHEME + url[7:]
    return None


@register.filter
@stringfilter
def colorpicker(value: str | None, colors: str) -> str:
    """
    Given set of colors, picks a color from comma-separated list
    based on initial character of string.

    Example:

    {{ user.username|colorpicker:"#00ff00,#ff0000,#0000ff" }}
    """
    choices = colors.split(",")
    return choices[ord(value[0] if value else " ") % len(choices)]


def auth_redirect_url(url: str, redirect_url: str) -> str:

    return (
        redirect_url
        if url.startswith("/account/")
        else f"{redirect_url}?{REDIRECT_FIELD_NAME}={urlencode(url)}"
    )


def build_absolute_uri(
    url: str | None = None, request: HttpRequest | None = None
) -> str:
    if request:
        return request.build_absolute_uri(url)

    # in case we don't have a request, e.g. in email job
    domain = Site.objects.get_current().domain
    protocol = "https" if settings.SECURE_SSL_REDIRECT else "http"
    base_url = protocol + "://" + domain

    return parse.urljoin(base_url, url) if url else base_url
