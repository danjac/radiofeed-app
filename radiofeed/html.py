import dataclasses
import functools
import html
import io
import re
from collections.abc import Iterator
from typing import Final

import bs4
import nh3
from bs4.element import Tag
from django.template.defaultfilters import striptags
from markdown_it import MarkdownIt

_RE_EXTRA_SPACES: Final = r" +"

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

_LINKIFY_PATTERN: Final = re.compile(
    r"(?P<url>(?:(?:https?|ftp)://|www\.)[^\s<]+)",
    re.IGNORECASE,
)
_TRAILING_PUNCTUATION: Final = ",.;:!?)]}"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class UrlMatch:
    """Data class representing recommend match in text."""

    start: int
    end: int
    url: str
    trailing: str

    def normalize_url(self) -> str:
        """Returns the normalized URL, adding https:// if needed."""
        if self.url.lower().startswith("www."):
            return f"https://{self.url}"
        return self.url


def render_markdown(content: str) -> str:
    """Scrubs any unwanted HTML tags and attributes and renders Markdown to HTML."""
    if content := content.strip():
        # render Markdown if not already HTML
        if not nh3.is_html(content):
            content = _markdown().render(content)

        return _clean_html(linkify(content))
    return ""


def strip_html(content: str) -> str:
    """Scrubs all HTML tags and entities from text.
    Removes content from any style or script tags.

    If content is Markdown, will attempt to render to HTML first.
    """
    return strip_extra_spaces(
        html.unescape(
            striptags(
                render_markdown(content),
            )
        )
    )


def strip_extra_spaces(value: str) -> str:
    """Removes any extra linebreaks and spaces."""
    lines = [
        line
        for line in [
            _re_extra_spaces().sub(" ", line).strip() for line in value.splitlines()
        ]
        if line
    ]
    return "\n".join(lines)


def make_soup(content: str) -> bs4.BeautifulSoup:
    """Makes a BeautifulSoup object from the given HTML content."""
    with io.StringIO(content) as fp:
        return bs4.BeautifulSoup(fp, "html.parser")


def linkify(content: str) -> str:
    """Converts URLs to links, if not already in <a> tags."""
    soup = make_soup(content)
    for node in list(soup.find_all(string=True)):
        if not node.parent or node.parent.name == "a":
            continue

        if replacements := list(insert_links(soup, str(node))):
            for replacement in replacements:
                node.insert_before(replacement)
            node.extract()

    return str(soup)


def insert_links(soup: bs4.BeautifulSoup, text: str) -> Iterator[str | Tag]:
    """Yields text and link tags for the given text, replacing URLs with <a> tags."""
    last_index = 0
    for match in find_url_matches(text):
        if match.start > last_index and (head := text[last_index : match.start]):
            yield head

        anchor = soup.new_tag("a", href=match.normalize_url())
        anchor["rel"] = _LINK_REL
        anchor.string = match.url
        yield anchor

        if match.trailing:
            yield match.trailing

        last_index = match.end

    if last_index < len(text) and (tail := text[last_index:]):
        yield tail


def find_url_matches(text: str) -> Iterator[UrlMatch]:
    """Finds URLs in the given text and yields UrlMatch objects."""
    for match in _LINKIFY_PATTERN.finditer(text):
        start, end = match.span()

        group = match.group("url")
        url, trailing = _strip_trailing_punctuation(group)

        if url:
            yield UrlMatch(
                start=start,
                end=end,
                url=url,
                trailing=trailing,
            )


def _strip_trailing_punctuation(url: str) -> tuple[str, str]:
    trailing = ""
    while url and url[-1] in _TRAILING_PUNCTUATION:
        trailing = url[-1] + trailing
        url = url[:-1]
    return url, trailing


def _clean_html(content: str) -> str:
    return nh3.clean(
        content,
        clean_content_tags=_CLEAN_TAGS,
        link_rel=_LINK_REL,
        set_tag_attribute_values=_TAG_ATTRIBUTES,
        tags=_ALLOWED_TAGS,
    )


@functools.cache
def _re_extra_spaces() -> re.Pattern:
    return re.compile(_RE_EXTRA_SPACES)


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
