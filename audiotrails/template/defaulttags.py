import collections
import json

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
def active_link(context, url_name, *args, **kwargs):
    url = resolve_url(url_name, *args, **kwargs)
    if context["request"].path == url:
        return ActiveLink(url, True, True)
    elif context["request"].path.startswith(url):
        return ActiveLink(url, True, False)
    return ActiveLink(url, False, False)


@register.filter
@stringfilter
def clean_html(value):
    return mark_safe(_stripentities(clean_html_content(value or "")))


@register.filter
@stringfilter
def stripentities(value):
    return _stripentities(value or "")


@register.filter
def percent(value, total):
    if not value or not total:
        return 0

    if (pc := (value / total) * 100) > 100:
        return 100
    return pc


@register.filter
def jsonify(value):
    return mark_safe(json.dumps(value, cls=DjangoJSONEncoder).translate(json_escapes))


@register.filter
def keepspaces(text):
    # changes any <br /> <p> <li> etc to spaces
    if text is None:
        return ""
    if not (text := text.strip()):
        return ""
    if (tag := bs4.BeautifulSoup(text, features="lxml").find("body")) is None:
        return ""
    return tag.get_text(separator=" ").strip()


@register.filter
def htmlattrs(attrs):
    if not attrs:
        return ""
    return mark_safe(" ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items()))


@register.filter
def login_url(url):
    return f"{reverse('account_login')}?{REDIRECT_FIELD_NAME}={urlencode(url)}"


@register.filter
def signup_url(url):
    return f"{reverse('account_signup')}?{REDIRECT_FIELD_NAME}={urlencode(url)}"


@register.simple_tag
def get_privacy_details():
    return settings.PRIVACY_DETAILS


@register.inclusion_tag("icons/_svg.html")
def icon(name, css_class="", title="", **attrs):
    return {
        "name": name,
        "css_class": css_class,
        "title": title,
        "attrs": attrs,
        "svg_template": f"icons/_{name}.svg",
    }


@register.inclusion_tag("forms/_button.html")
def button(
    text,
    icon="",
    type="default",
    css_class="",
    **attrs,
):
    return {
        "text": text,
        "icon": icon,
        "type": type,
        "css_class": css_class,
        "tag": "a" if "href" in attrs else "button",
        "attrs": attrs,
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
