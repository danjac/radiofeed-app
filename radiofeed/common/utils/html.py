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
    """Runs Bleach through value and scrubs any unwanted HTML tags and attributes.

    Args:
        value (str)

    Returns:
        str
    """
    return (
        bleach.linkify(
            bleach.clean(
                value,
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRS,
                strip=True,
            ),
            [linkify_callback],
        )
        if value
        else ""
    )


def strip_whitespace(value):
    """Removes all trailing whitespace. Any None value just returns an empty string.

    Args:
        value (str | None)

    Returns:
        str
    """
    return (value or "").strip()


def strip_html(value):
    """Scrubs all HTML tags and entities from text.

    Args:
        value (str | None): text to be cleaned

    Returns:
        str
    """
    return html.unescape(striptags(strip_whitespace(value)))


def as_html(value):
    """Checks if content contains any HTML tags. If not, will try and
    parse Markdown from text.

    Args:
        value (str)

    Returns:
        str: HTML content
    """
    return value if HTML_RE.match(value) else markdown.markdown(value)


def markup(value):
    """Parses Markdown and/or html and returns cleaned result.

    Args:
        value (str | None)

    Returns:
        str

    """
    if value := strip_whitespace(value):
        return html.unescape(clean(as_html(value)))
    return ""
