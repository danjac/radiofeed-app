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
from django.shortcuts import resolve_url
from django.template.defaultfilters import stringfilter, urlencode
from django.urls import reverse
from django.utils.safestring import mark_safe

from jcasts.shared import cleaners

register = template.Library()


ActiveLink = collections.namedtuple("ActiveLink", "url match exact")

_validate_url = URLValidator(["http", "https"])


@register.simple_tag(takes_context=True)
def absolute_uri(context, url=None, *args, **kwargs):

    url = resolve_url(url, *args, **kwargs) if url else None

    if "request" in context:
        return context["request"].build_absolute_uri(url)

    # in case we don't have a request, e.g. in email job
    domain = Site.objects.get_current().domain
    protocol = "https" if settings.SECURE_SSL_REDIRECT else "http"
    base_url = protocol + "://" + domain

    return parse.urljoin(base_url, url) if url else base_url


@register.filter
def format_duration(total_seconds):
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
def active_link(context, url_name, *args, **kwargs):
    url = resolve_url(url_name, *args, **kwargs)

    if context["request"].path == url:
        return ActiveLink(url, True, True)

    if context["request"].path.startswith(url):
        return ActiveLink(url, True, False)

    return ActiveLink(url, False, False)


@register.simple_tag(takes_context=True)
def re_active_link(context, url_name, pattern, *args, **kwargs):
    url = resolve_url(url_name, *args, **kwargs)
    if re.match(pattern, context["request"].path):
        return ActiveLink(url, True, False)

    return ActiveLink(url, False, False)


@register.simple_tag
def get_contact_details():
    return settings.CONTACT_DETAILS


@register.filter(is_safe=True)
@stringfilter
def markup(value):
    return mark_safe(cleaners.markup(value))  # nosec


@register.filter
def login_url(url):
    return _redirect_to_auth_url(url, reverse("account_login"))


@register.filter
def signup_url(url):
    return _redirect_to_auth_url(url, reverse("account_signup"))


@register.inclusion_tag("icons/_svg.html")
def icon(name, css_class="", title="", **attrs):
    return {
        "name": name,
        "css_class": css_class,
        "title": title,
        "attrs": attrs,
        "svg_template": f"icons/_{name}.svg",
    }


@register.inclusion_tag("_share_buttons.html", takes_context=True)
def share_buttons(context, url, subject, css_class=""):
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
def cookie_notice(context):
    return {"accept_cookies": "accept-cookies" in context["request"].COOKIES}


@register.filter
@stringfilter
def normalize_url(url):
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


@register.filter
def safe_url(url):
    if not url or url.startswith("https://"):
        return url
    if url.startswith("http://"):
        return "https://" + url[7:]
    return None


@register.filter
@stringfilter
def colorpicker(value, colors):
    """
    Given set of colors, picks a color from comma-separated list
    based on initial value of string.

    Example:

    {{ user.username|colorpicker:"#00ff00,#ff0000,#0000ff" }}
    """
    choices = colors.split(",")
    return choices[ord(value[0] if value else " ") % len(choices)]


def _redirect_to_auth_url(url, redirect_url):

    return (
        redirect_url
        if url.startswith("/account/")
        else f"{redirect_url}?{REDIRECT_FIELD_NAME}={urlencode(url)}"
    )
