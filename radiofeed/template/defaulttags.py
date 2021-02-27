import collections
import json

from typing import Any, Dict, Optional
from urllib.urlparse import parse

import bs4

from django import template
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.serializers.json import DjangoJSONEncoder
from django.forms import Field
from django.shortcuts import resolve_url
from django.template.context import Context
from django.template.defaultfilters import stringfilter, urlencode
from django.urls import reverse
from django.utils.safestring import mark_safe

from .html import clean_html_content
from .html import stripentities as _stripentities

register = template.Library()


ActiveLink = collections.namedtuple("ActiveLink", "url match exact")


json_escapes = {
    ord(">"): "\\u003E",
    ord("<"): "\\u003C",
    ord("&"): "\\u0026",
    ord("'"): "\\u0027",
}


@register.simple_tag(takes_context=True)
def active_link(context: Context, url_name: str, *args, **kwargs) -> ActiveLink:
    url = resolve_url(url_name, *args, **kwargs)
    if context["request"].path == url:
        return ActiveLink(url, True, True)
    elif context["request"].path.startswith(url):
        return ActiveLink(url, True, False)
    return ActiveLink(url, False, False)


@register.filter
def widget_type(field: Field) -> str:
    return field.field.widget.input_type


@register.filter
@stringfilter
def clean_html(value: str) -> str:
    return mark_safe(_stripentities(clean_html_content(value or "")))


@register.filter
@stringfilter
def stripentities(value: str) -> str:
    return _stripentities(value or "")


@register.filter
def percent(value: Optional[float], total: Optional[float]) -> float:
    if not value or not total:
        return 0

    return (value / total) * 100


@register.filter
def jsonify(value: Any) -> str:
    return mark_safe(json.dumps(value, cls=DjangoJSONEncoder).translate(json_escapes))


@register.filter
def keepspaces(text: Optional[str]) -> str:
    # changes any <br /> <p> <li> etc to spaces
    if not text:
        return ""
    return (
        bs4.BeautifulSoup(text, features="lxml")
        .find("body")
        .get_text(separator=" ")
        .strip()
    )


@register.filter
def htmlattrs(attrs: Dict) -> str:
    if not attrs:
        return ""
    return mark_safe(
        " ".join([f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items()])
    )


@register.filter
def login_url(url: str) -> str:
    return f"{reverse('account_login')}?{REDIRECT_FIELD_NAME}={urlencode(url)}"


@register.inclusion_tag("components/icons/_svg.html")
def icon(name: str, css_class: str = "", title: str = "", **attrs) -> Dict:
    return {
        "name": name,
        "css_class": css_class,
        "title": title,
        "attrs": attrs,
        "svg_template": f"components/icons/_{name}.svg",
    }


@register.inclusion_tag("forms/_button.html")
def button(
    text: str,
    icon: str = "",
    type: str = "default",
    css_class: str = "",
    **attrs,
) -> Dict:
    return {
        "text": text,
        "icon": icon,
        "type": type,
        "css_class": css_class,
        "tag": "a" if "href" in attrs else "button",
        "attrs": attrs,
    }


@register.inclusion_tag("_share_buttons.html", takes_context=True)
def share_buttons(
    context: Context, url: str, subject: str, css_class: str = ""
) -> Dict:
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
