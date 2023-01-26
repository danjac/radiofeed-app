from __future__ import annotations

import html

from typing import Final

from django.template.defaultfilters import striptags
from django.utils.safestring import mark_safe
from lxml.html.clean import Cleaner
from markdown_it import MarkdownIt

_ALLOWED_TAGS: Final = {
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
}

_markdown = MarkdownIt()

_cleaner = Cleaner(allow_tags=_ALLOWED_TAGS, safe_attrs_only=True, add_nofollow=True)


def clean(value: str) -> str:
    """Scrubs any unwanted HTML tags and attributes."""
    return _cleaner.clean_html(value) if value else ""


def strip_html(value: str) -> str:
    """Scrubs all HTML tags and entities from text."""
    return html.unescape(striptags(value.strip()))


def markdown(value: str) -> str:
    """Returns safe Markdown rendered string. If content is already HTML will pass as-is."""
    if value := value.strip():
        return mark_safe(clean(_markdown.render(value)))  # nosec
    return ""
