import html
from typing import Generator, List, Optional, Tuple

import bleach
from html5lib.filters import optionaltags, whitespace

Attribute = Tuple[Optional[str], str]
AttributeList = List[Attribute]


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
    tags=bleach.ALLOWED_TAGS + ["p", "div", "br"],
    strip=True,
    filters=[whitespace.Filter, RemoveEmptyFilter],
)


def linkify_callback(attrs: AttributeList, new: bool = False) -> AttributeList:
    attrs[(None, "target")] = "_blank"
    attrs[(None, "rel")] = "noopener noreferrer nofollow"
    return attrs


def clean_html_content(value: Optional[str]) -> str:
    try:
        return bleach.linkify(cleaner.clean(value), [linkify_callback]) if value else ""
    except (ValueError, TypeError):
        return ""


def stripentities(value: Optional[str]) -> str:
    """Removes any HTML entities such as &nbsp; and replaces
    them with plain ASCII equivalents."""
    return html.unescape(value) if value else ""
