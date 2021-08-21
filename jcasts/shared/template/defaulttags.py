from __future__ import annotations

import collections
import math
import re

from urllib import parse

import bs4

from django import template
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.shortcuts import resolve_url
from django.template.defaultfilters import stringfilter, urlencode
from django.urls import reverse

from jcasts.shared import cleaners
from jcasts.shared.typedefs import ContextDict

register = template.Library()


ActiveLink = collections.namedtuple("ActiveLink", "url match exact")

_validate_url = URLValidator(["http", "https"])


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
def active_link(context: ContextDict, url_name: str, *args, **kwargs) -> ActiveLink:
    url = resolve_url(url_name, *args, **kwargs)

    if context["request"].path == url:
        return ActiveLink(url, True, True)

    if context["request"].path.startswith(url):
        return ActiveLink(url, True, False)

    return ActiveLink(url, False, False)


@register.simple_tag(takes_context=True)
def re_active_link(
    context: ContextDict, url_name: str, pattern: str, *args, **kwargs
) -> ActiveLink:
    url = resolve_url(url_name, *args, **kwargs)
    if re.match(pattern, context["request"].path):
        return ActiveLink(url, True, False)

    return ActiveLink(url, False, False)


@register.filter(is_safe=True)
@stringfilter
def markup(value: str) -> str:
    return cleaners.markup(value)


@register.filter
@stringfilter
def unescape(value: str) -> str:
    return cleaners.unescape(value)


@register.filter
@register.filter
def keepspaces(text: str | None) -> str:
    # changes any <br /> <p> <li> etc to spaces
    if text is None:
        return ""
    if not (text := text.strip()):
        return ""
    tag = bs4.BeautifulSoup(text, features="lxml").find("body")
    return tag.get_text(separator=" ").strip() if tag else text


@register.filter
def login_url(url: str) -> str:
    return f"{reverse('account_login')}?{REDIRECT_FIELD_NAME}={urlencode(url)}"


@register.filter
def signup_url(url: str) -> str:
    return f"{reverse('account_signup')}?{REDIRECT_FIELD_NAME}={urlencode(url)}"


@register.simple_tag
def get_privacy_details() -> dict[str, str]:
    return settings.PRIVACY_DETAILS


@register.simple_tag
def get_twitter_account() -> str | None:
    return settings.TWITTER_ACCOUNT


@register.inclusion_tag("icons/_svg.html")
def icon(name: str, css_class: str = "", title: str = "", **attrs: str) -> ContextDict:
    return {
        "name": name,
        "css_class": css_class,
        "title": title,
        "attrs": attrs,
        "svg_template": f"icons/_{name}.svg",
    }


@register.inclusion_tag("_share_buttons.html", takes_context=True)
def share_buttons(
    context: ContextDict, url: str, subject: str, css_class: str = ""
) -> ContextDict:
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


@register.filter
@stringfilter
def normalize_url(url: str | None) -> str:
    """If a URL is provided minus http(s):// prefix, prepends protocol."""
    if not url:
        return ""
    for value in (url, "https://" + url):
        try:
            _validate_url(value)
            return value
        except ValidationError:
            pass
    return ""
