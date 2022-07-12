from __future__ import annotations

import html
import re

from typing import Final

import bleach
import markdown

from django.template.defaultfilters import striptags

_ALLOWED_TAGS: Final = [
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
    "img",
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
]

_ALLOWED_ATTRS: Final = {
    "a": ["href", "target", "title"],
    "img": ["src", "alt", "height", "width", "loading"],
}

_HTML_RE = re.compile(r"^(<\/?[a-zA-Z][\s\S]*>)+", re.UNICODE)


def clean(value: str) -> str:
    """Runs Bleach through value and scrubs any unwanted HTML tags and attributes."""
    return (
        bleach.linkify(
            bleach.clean(
                value,
                attributes=_ALLOWED_ATTRS,
                tags=_ALLOWED_TAGS,
                strip=True,
            ),
            [_linkify_callback],  # type: ignore
        )
        if value
        else ""
    )


def strip_whitespace(value: str | None) -> str:
    """Removes all trailing whitespace. Any None value just returns an empty string."""
    return (value or "").strip()


def strip_html(value: str | None) -> str:
    """Scrubs all HTML tags and entities from text."""
    return html.unescape(striptags(strip_whitespace(value)))


def as_html(value: str) -> str:
    """Checks if content contains any HTML tags. If not, will try and parse Markdown from text."""
    return value if _HTML_RE.match(value) else markdown.markdown(value)


def markup(value: str | None) -> str:
    """Parses Markdown and/or html and returns cleaned result."""
    if value := strip_whitespace(value):
        return html.unescape(clean(as_html(value)))
    return ""


def _linkify_callback(attrs: dict, new: bool = False) -> dict:
    attrs[(None, "target")] = "_blank"
    attrs[(None, "rel")] = "noopener noreferrer nofollow"
    return attrs
