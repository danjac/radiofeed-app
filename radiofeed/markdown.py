import functools
from typing import Final

import nh3
from django.utils.safestring import mark_safe
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
        "target": "_blank",
    },
}


@mark_safe  # noqa: S308
def markdownify(content: str) -> str:
    """Scrubs any unwanted HTML tags and attributes and renders Markdown to HTML."""
    return nh3.clean(
        _markdown().render(content),
        clean_content_tags=_CLEAN_TAGS,
        link_rel=_LINK_REL,
        set_tag_attribute_values=_TAG_ATTRIBUTES,
        tags=_ALLOWED_TAGS,
    )


@functools.cache
def _markdown():
    return MarkdownIt(
        "commonmark",
        {
            "linkify": True,
            "typographer": True,
        },
    ).enable(
        [
            "linkify",
            "replacements",
            "smartquotes",
        ]
    )
