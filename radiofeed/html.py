from __future__ import annotations

import html

from django.template.defaultfilters import striptags
from django.utils.safestring import mark_safe
from lxml.html.clean import Cleaner
from markdown import markdown as _markdown

_cleaner = Cleaner(
    allow_tags=[
        "a",
        "abbr",
        "acronym",
        "address",
        "b",
        "br",
        "div",
        "dl",
        "dt",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "li",
        "ol",
        "p",
        "pre",
        "q",
        "s",
        "small",
        "strike",
        "strong",
        "span",
        "style",
        "sub",
        "sup",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "tt",
        "u",
        "ul",
    ],
    safe_attrs_only=True,
    add_nofollow=True,
)


def clean(value: str | None) -> str:
    """Runs Bleach through value and scrubs any unwanted HTML tags and attributes."""
    return _cleaner.clean_html(value) if value else ""


def strip_whitespace(value: str | None) -> str:
    """Removes all trailing whitespace."""
    return (value or "").strip()


def strip_html(value: str | None) -> str:
    """Scrubs all HTML tags and entities from text."""
    return html.unescape(striptags(strip_whitespace(value)))


def markdown(value: str | None) -> str:
    """Returns safe Markdown rendered string. If content is already HTML will pass as-is."""
    if value := strip_whitespace(value):
        return mark_safe(clean(_markdown(value)))  # nosec
    return ""
