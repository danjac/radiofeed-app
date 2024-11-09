import functools
import html
import re
from collections.abc import Iterator
from typing import Final

import nh3
from django.template.defaultfilters import striptags
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

_RE_EXTRA_SPACES: Final = r" +"

_RE_URL: Final = (
    r'((?:<a href[^>]+>)|(?:<a href="))?'
    r"((?:https?):(?:(?://)|(?:\\\\))+"
    r"(?:[\w\d:#@%/;$()~_?\+\-=\\\.&](?:#!)?)*)"
)

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
def render_markdown(value: str) -> str:
    """Scrubs any unwanted HTML tags and attributes and renders Markdown to HTML."""
    if value := value.strip():
        return nh3.clean(
            urlize(value if nh3.is_html(value) else _markdown().render(value)),
            clean_content_tags=_CLEAN_TAGS,
            link_rel=_LINK_REL,
            set_tag_attribute_values=_TAG_ATTRIBUTES,
            tags=_ALLOWED_TAGS,
        )
    return ""


def strip_html(value: str) -> str:
    """Scrubs all HTML tags and entities from text.
    Removes content from any style or script tags.

    If content is Markdown, will attempt to render to HTML first.
    """
    return strip_extra_spaces(
        html.unescape(
            striptags(
                render_markdown(value),
            )
        )
    )


def urlize(value: str) -> str:
    """Converts URLs in text to HTML links, unless already in a link."""
    return re.sub(_re_url(), _urlize, value)


def _urlize(match: re.Match) -> str:
    href_tag, url = match.groups()
    if href_tag:
        # Since it has an href tag, this isn't what we want to change,
        # so return the whole match.
        return match.group(0)
    return f'<a href="{url}">{url}</a>'


def strip_extra_spaces(value: str) -> str:
    """Removes any extra linebreaks and spaces."""
    return "\n".join(_strip_spaces_from_lines(value)).strip()


def _strip_spaces_from_lines(value: str) -> Iterator[str]:
    for line in value.splitlines():
        if stripped := re.sub(_RE_EXTRA_SPACES, " ", line).strip():
            yield stripped


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


@functools.cache
def _re_url():
    return re.compile(_RE_URL, flags=re.IGNORECASE)
