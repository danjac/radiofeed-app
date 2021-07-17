from __future__ import annotations

import html

import bleach

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

ALLOWED_ATTRS = {
    "a": ["href", "target", "title"],
}


cleaner = bleach.Cleaner(
    attributes=ALLOWED_ATTRS,
    tags=ALLOWED_TAGS,
    strip=True,
    filters=[whitespace.Filter],
)


def linkify_callback(attrs: dict, new: bool = False) -> dict:
    attrs[(None, "target")] = "_blank"
    attrs[(None, "rel")] = "noopener noreferrer nofollow"
    return attrs


def clean_html_content(value: str | None) -> str:
    return bleach.linkify(cleaner.clean(value), [linkify_callback]) if value else ""  # type: ignore


def unescape(value: str | None) -> str:
    """Removes any HTML entities such as &nbsp; and replaces
    them with plain ASCII equivalents."""
    return html.unescape(value) if value else ""
