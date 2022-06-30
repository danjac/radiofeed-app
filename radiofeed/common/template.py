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
from django.shortcuts import resolve_url
from django.template.defaultfilters import stringfilter, urlencode
from django.urls import reverse
from django.utils.safestring import mark_safe

from radiofeed.common import html

register = template.Library()


@dataclasses.dataclass
class ActiveLink:
    url: str
    match: bool = False
    exact: bool = False


_validate_url = URLValidator(["http", "https"])


@register.simple_tag(takes_context=True)
def pagination_url(context, page_number, param="page"):
    """
    Inserts the "page" query string parameter with the
    provided page number into the template, preserving the original
    request path and any other query string parameters.

    Given the above and a URL of "/search?q=test" the result would
    be something like:

    "/search?q=test&page=3"

    Args:
        context (dict): template context
        page_number (int)
        param (str): query string parameter for pages

    Returns:
        str: updated URL path with new page
    """
    request = context["request"]
    params = request.GET.copy()
    params[param] = page_number
    return request.path + "?" + params.urlencode()


@register.simple_tag
def get_site_config():
    """
    Returns:
        dict: site configuration
    """
    return settings.SITE_CONFIG


@register.simple_tag(takes_context=True)
def absolute_uri(context, url=None, *args, **kwargs):
    """Generate absolute URI based on server environment or current Site.

    Args:
        context (dict): template context
        url (str): URL name or path

    Returns:
        str
    """
    return build_absolute_uri(
        resolve_url(url, *args, **kwargs) if url else None, context.get("request")
    )


@register.filter
def format_duration(total_seconds):
    """Formats duration (in seconds) as human readable value e.g. 1h 30min

    Args:
        total_seconds (int | None)

    Returns:
        str: empty if total seconds None or under a minute
    """
    if total_seconds is None or total_seconds < 60:
        return ""

    rv = []

    if total_hours := math.floor(total_seconds / 3600):
        rv.append(f"{total_hours}h")

    if total_minutes := round((total_seconds % 3600) / 60):
        rv.append(f"{total_minutes}min")

    return " ".join(rv)


@register.simple_tag(takes_context=True)
def active_link(context, url_name, *args, **kwargs):
    """Returns url with active link info

    Args:
        context (dict): template context
        url_name (str): URL name

    Returns:
        ActiveLink
    """
    url = resolve_url(url_name, *args, **kwargs)

    if context["request"].path == url:
        return ActiveLink(url, match=True, exact=True)

    if context["request"].path.startswith(url):
        return ActiveLink(url, match=True)

    return ActiveLink(url)


@register.simple_tag(takes_context=True)
def re_active_link(context, url_name, pattern, *args, **kwargs):
    """Returns url with active link info

    Args:
        context (dict): template context
        url_name (str): URL name
        pattern (str): regex pattern to match

    Returns:
        ActiveLink
    """
    url = resolve_url(url_name, *args, **kwargs)
    if re.match(pattern, context["request"].path):
        return ActiveLink(url, match=True)

    return ActiveLink(url)


@register.filter
def login_url(url):
    """Returns login URL with redirect parameter back to this url

    Args:
        url (str)

    Returns:
        str
    """
    return auth_redirect_url(url, reverse("account_login"))


@register.filter
def signup_url(url):
    """Returns signup URL with redirect parameter back to this url

    Args:
        url (str)

    Returns:
        str
    """
    return auth_redirect_url(url, reverse("account_signup"))


@register.inclusion_tag("includes/markdown.html")
def markdown(value):
    """Renders markdown content

    Args:
        value (str | None)

    Returns:
        dict: context with `content` of markdown value
    """
    return {"content": mark_safe(html.markup(value))}  # nosec


@register.inclusion_tag("includes/share_buttons.html", takes_context=True)
def share_buttons(context, url, subject, css_class=""):
    """Render set of share buttons for a page for email, Facebook, Twitter
    and Linkedin.

    Args:
        url (str): URL on page to share in link (automatically expanded to
            absolute URI)
        subject (str): subject line
        css_class (str): CSS classes to render in button

    Returns:
        dict
    """
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


@register.inclusion_tag("includes/cookie_notice.html", takes_context=True)
def cookie_notice(context):
    """
    Renders GDPR cookie notice. Notice should be hidden once user has clicked
    "Accept Cookies" button.

    Args:
        context (dict): request context

    Returns:
        dict
    """

    return {"accept_cookies": "accept-cookies" in context["request"].COOKIES}


@register.filter
@stringfilter
def normalize_url(url):
    """If a URL is provided minus http(s):// prefix, prepends protocol.

    Args:
        url (str)

    Returns:
        str
    """
    if url:
        for value in (url, "https://" + url):
            try:
                _validate_url(value)
                return value
            except ValidationError:
                continue
    return ""


def auth_redirect_url(url, redirect_url):

    return (
        redirect_url
        if url.startswith("/account/")
        else f"{redirect_url}?{REDIRECT_FIELD_NAME}={urlencode(url)}"
    )


def build_absolute_uri(url=None, request=None):
    if request:
        return request.build_absolute_uri(url)

    # in case we don't have a request, e.g. in email job
    domain = Site.objects.get_current().domain
    protocol = "https" if settings.SECURE_SSL_REDIRECT else "http"
    base_url = protocol + "://" + domain

    return parse.urljoin(base_url, url) if url else base_url
