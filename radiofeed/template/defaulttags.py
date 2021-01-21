# Standard Library
import collections

# Django
from django import template
from django.shortcuts import resolve_url
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

# Local
from .html import clean_html_content
from .html import stripentities as _stripentities

register = template.Library()

ActiveLink = collections.namedtuple("Link", "url match exact")


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

    return (value / total) * 100
