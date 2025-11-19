import functools
from typing import Final

import nh3
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

from radiofeed.linkifier import linkify

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
    if content := content.strip():
        # render Markdown if not already HTML
        if not nh3.is_html(content):
            content = _markdown().render(content)
        return _clean_html(linkify(content))
    return ""


def _clean_html(content: str) -> str:
    return nh3.clean(
        content,
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
