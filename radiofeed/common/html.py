import html
import re

import bleach
import markdown

from django.template.defaultfilters import striptags

ALLOWED_TAGS = [
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

ALLOWED_ATTRS = {
    "a": ["href", "target", "title"],
    "img": ["src", "alt", "height", "width", "loading"],
}

HTML_RE = re.compile(r"^(<\/?[a-zA-Z][\s\S]*>)+", re.UNICODE)


def linkify_callback(attrs, new=False):
    attrs[(None, "target")] = "_blank"
    attrs[(None, "rel")] = "noopener noreferrer nofollow"
    return attrs


def clean(value):
    return (
        bleach.linkify(
            bleach.clean(
                value,
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRS,
                strip=True,
            ),
            [linkify_callback],  # type: ignore
        )
        if value
        else ""
    )


def strip_whitespace(value):
    return (value or "").strip()


def strip_html(value):
    """Removes all HTML tags and entities"""
    return html.unescape(striptags(strip_whitespace(value)))


def as_html(value):
    return value if HTML_RE.match(value) else markdown.markdown(value)


def markup(value):
    """Parses Markdown and/or html and returns cleaned result."""
    if value := strip_whitespace(value):
        return html.unescape(clean(as_html(value)))
    return ""
