import functools
import html
from typing import Final

import nh3
from django.template.defaultfilters import striptags
from markdown_it import MarkdownIt

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

_CLEAN_TAGS: Final = {
    "script",
    "style",
}

_LINK_REL: Final = "noopener noreferrer nofollow"

_TAG_ATTRIBUTES: Final = {
    "a": {
        "class": "link",
        "target": "_blank",
    },
}


@functools.cache
def _markdown():
    return MarkdownIt("commonmark", {"linkify": True}).enable("linkify")


def clean_html(value: str) -> str:
    """Scrubs any unwanted HTML tags and attributes."""
    if value := value.strip():
        return nh3.clean(
            value if nh3.is_html(value) else _markdown().render(value),
            clean_content_tags=_CLEAN_TAGS,
            link_rel=_LINK_REL,
            set_tag_attribute_values=_TAG_ATTRIBUTES,
            tags=_ALLOWED_TAGS,
        )
    return ""


def strip_html(value: str) -> str:
    """Scrubs all HTML tags and entities from text."""
    return html.unescape(striptags(value.strip()))
