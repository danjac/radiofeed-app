import html

from typing import Dict, Generator, Optional, Tuple

import bleach

from html5lib.filters import optionaltags, whitespace

Attribute = Tuple[Optional[str], str]
AttributeDict = Dict[Attribute, str]


def allow_src(tag, name, value):
    if name in ("alt", "height", "width"):
        return True
    if name == "src":
        return value.startswith("https://")
    return False


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
    "img": allow_src,
}


class RemoveEmptyFilter(optionaltags.Filter):
    """Remove stray paragraphs with no content"""

    elements = frozenset(["p"])

    def __iter__(self) -> Generator:
        remove = False
        for _, token, next in self.slider():
            if token["type"] == "StartTag" and token["name"] in self.elements:
                if (
                    next["type"] == "Character"
                    and next["data"] == ""
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


def linkify_callback(attrs: AttributeDict, new: bool = False) -> AttributeDict:
    attrs[(None, "target")] = "_blank"
    attrs[(None, "rel")] = "noopener noreferrer nofollow"
    attrs[(None, "data-turbo-frame")] = "_top"
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
