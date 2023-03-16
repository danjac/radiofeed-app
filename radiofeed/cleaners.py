from __future__ import annotations

import html

from typing import Final

import nh3

from django.template.defaultfilters import striptags

_ALLOWED_TAGS: Final = {
    "a",
    "abbr",
    "acronym",
    "address",
    "b",
    "br",
    "code",
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
}


def clean_html(value: str) -> str:
    """Scrubs any unwanted HTML tags and attributes."""
    return (
        (
            nh3.clean(
                value,
                tags=_ALLOWED_TAGS,
                link_rel="noopener noreferrer nofollow",
            )
        )
        if (value := value.strip())
        else ""
    )


def strip_html(value: str) -> str:
    """Scrubs all HTML tags and entities from text."""
    return html.unescape(striptags(value.strip()))
