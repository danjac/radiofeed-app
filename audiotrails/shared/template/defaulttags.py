import collections
import json
import math

from typing import Any, Dict, Optional
from urllib import parse

import bs4

from django import template
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import resolve_url
from django.template.defaultfilters import stringfilter, urlencode
from django.urls import reverse
from django.utils.safestring import mark_safe

from ..html import clean_html_content
from ..html import stripentities as _stripentities
from ..types import Context

register = template.Library()


ActiveLink = collections.namedtuple("ActiveLink", "url match exact")


json_escapes = {
    ord(">"): "\\u003E",
    ord("<"): "\\u003C",
    ord("&"): "\\u0026",
    ord("'"): "\\u0027",
}


@register.filter
def format_duration(total_seconds: Optional[int]) -> str:
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
def active_link(context: Context, url_name: str, *args, **kwargs) -> ActiveLink:
    url = resolve_url(url_name, *args, **kwargs)
    if context["request"].path == url:
        return ActiveLink(url, True, True)
    elif context["request"].path.startswith(url):
        return ActiveLink(url, True, False)
    return ActiveLink(url, False, False)


@register.filter
@stringfilter
def clean_html(value: str) -> str:
    return mark_safe(_stripentities(clean_html_content(value or "")))


@register.filter
@stringfilter
def stripentities(value: str) -> str:
    return _stripentities(value or "")


@register.filter
def percent(value: int, total: int) -> float:
    if not value or not total:
        return 0

    if (pc := (value / total) * 100) > 100:
        return 100
    return pc


@register.filter
def jsonify(value: Any) -> str:
    return mark_safe(json.dumps(value, cls=DjangoJSONEncoder).translate(json_escapes))


@register.filter
def keepspaces(text: Optional[str]) -> str:
    # changes any <br /> <p> <li> etc to spaces
    if text is None:
        return ""
    if not (text := text.strip()):
        return ""
    if (tag := bs4.BeautifulSoup(text, features="lxml").find("body")) is None:
        return ""
    return tag.get_text(separator=" ").strip()


@register.filter
def htmlattrs(attrs: Dict[str, str]) -> str:
    if not attrs:
        return ""
    return mark_safe(" ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items()))


@register.filter
def login_url(url: str) -> str:
    return f"{reverse('account_login')}?{REDIRECT_FIELD_NAME}={urlencode(url)}"


@register.filter
def signup_url(url: str) -> str:
    return f"{reverse('account_signup')}?{REDIRECT_FIELD_NAME}={urlencode(url)}"


@register.simple_tag
def get_privacy_details() -> Dict[str, str]:
    return settings.PRIVACY_DETAILS


@register.inclusion_tag("icons/_svg.html")
def icon(name: str, css_class: str = "", title: str = "", **attrs: str) -> Context:
    return {
        "name": name,
        "css_class": css_class,
        "title": title,
        "attrs": attrs,
        "svg_template": f"icons/_{name}.svg",
    }


@register.inclusion_tag("_share_buttons.html", takes_context=True)
def share_buttons(
    context: Context, url: str, subject: str, css_class: str = ""
) -> Context:
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
