import collections
import json
from typing import Any, Dict, Optional
from urllib import parse

from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import resolve_url
from django.template.context import RequestContext
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

import bs4

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
def active_link(context: RequestContext, url_name: str, *args, **kwargs) -> ActiveLink:
    url = resolve_url(url_name, *args, **kwargs)
    if context["request"].path == url:
        return ActiveLink(url, True, True)
    elif context["request"].path.startswith(url):
        return ActiveLink(url, True, False)
    return ActiveLink(url, False, False)


@register.inclusion_tag("share/_share_buttons.html", takes_context=True)
def share_buttons(context: RequestContext, url: str, subject: str):
    url = parse.quote(context["request"].build_absolute_uri(url))
    subject = parse.quote(subject)

    return {
        "share_urls": {
            "email": f"mailto:?subject={subject}&body={url}",
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={url}",
            "twitter": f"https://twitter.com/share?url={url}&text={subject}",
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={url}",
        }
    }


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
    return mark_safe(
        " ".join([f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items()])
    )


@register.inclusion_tag("svg/_svg.html")
def svg(name: str, css_class="", **attrs) -> Dict:
    return {
        "svg_template": f"svg/_{name}.svg",
        "css_class": css_class,
        "attrs": htmlattrs(attrs),
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
        "attrs": htmlattrs(attrs),
    }
