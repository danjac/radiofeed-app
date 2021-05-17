import html

from typing import Any, Generator, Optional

import bleach

from html5lib.filters import optionaltags, whitespace

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


class RemoveEmptyFilter(optionaltags.Filter):
    """Remove stray paragraphs with no content"""

    elements = frozenset(["p"])

    def __iter__(self) -> Generator[dict[str, Any], None, None]:
        remove = False
        for _, token, next in self.slider():
            if token["type"] == "StartTag" and token["name"] in self.elements:
                if (
                    next["type"] == "Characters"
                    and next["data"].strip() == ""
                    or next["type"] == "EmptyTag"
                ):
                    remove = True
                else:
                    remove = False
                    yield token
            elif not remove:
                remove = False
                yield token


cleaner = bleach.Cleaner(
    attributes=ALLOWED_ATTRS,
    tags=ALLOWED_TAGS,
    strip=True,
    filters=[whitespace.Filter, RemoveEmptyFilter],
)


def linkify_callback(attrs: dict, new: bool = False) -> dict:
    attrs[(None, "target")] = "_blank"
    attrs[(None, "rel")] = "noopener noreferrer nofollow"
    return attrs


def clean_html_content(value: Optional[str]) -> str:
    try:
        return bleach.linkify(cleaner.clean(value), [linkify_callback]) if value else ""  # type: ignore
    except (ValueError, TypeError):
        return ""


def stripentities(value: Optional[str]) -> str:
    """Removes any HTML entities such as &nbsp; and replaces
    them with plain ASCII equivalents."""
    return html.unescape(value) if value else ""
