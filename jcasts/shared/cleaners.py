from __future__ import annotations

import html
import re

import bleach
import markdown

from django.template.defaultfilters import striptags
from html5lib.filters import whitespace

ALLOWED_TAGS: list[str] = [
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
]

ALLOWED_ATTRS: dict[str, list[str]] = {
    "a": ["href", "target", "title"],
}

HTML_RE = re.compile(r"^(<\/?[a-zA-Z][\s\S]*>)+", re.UNICODE)

cleaner = bleach.Cleaner(
    attributes=ALLOWED_ATTRS,
    tags=ALLOWED_TAGS,
    strip=True,
    filters=[whitespace.Filter],
)


def linkify_callback(
    attrs: dict[tuple[str | None, str], str], new: bool = False
) -> dict[tuple[str | None, str], str]:
    attrs[(None, "target")] = "_blank"
    attrs[(None, "rel")] = "noopener noreferrer nofollow"
    return attrs


def clean(value: str | None) -> str:
    return bleach.linkify(cleaner.clean(value), [linkify_callback]) if value else ""  # type: ignore


def strip_whitespace(value: str | None) -> str:
    return (value or "").strip()


def strip_html(value: str | None) -> str:
    """Removes all HTML tags and entities"""
    return html.unescape(striptags(strip_whitespace(value)))


def as_html(value: str) -> str:
    if HTML_RE.match(value):
        return value
    return markdown.markdown(value)


def markup(value: str | None) -> str:
    """Parses Markdown and/or html and returns cleaned result."""
    if value := strip_whitespace(value):
        return html.unescape(clean(as_html(value)))
    return ""
