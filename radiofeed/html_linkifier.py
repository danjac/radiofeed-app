import dataclasses
import functools
import io
import re
from collections.abc import Iterator
from typing import Final

import bs4
from bs4.element import Tag

_TRAILING_PUNCTUATION: Final = ",.;:!?)]}"

_LINK_REL: Final = "noopener noreferrer nofollow"


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


def make_soup(content: str) -> bs4.BeautifulSoup:
    """Makes a BeautifulSoup object from the given HTML content."""
    with io.StringIO(content) as fp:
        return bs4.BeautifulSoup(fp, "html.parser")


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
    for match in _re_linkify_pattern().finditer(text):
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
    stripped = url.rstrip(_TRAILING_PUNCTUATION)
    trailing = url[len(stripped) :]
    return stripped, trailing


@functools.cache
def _re_linkify_pattern() -> re.Pattern:
    return re.compile(
        r"(?P<url>(?:(?:https?|ftp)://|www\.)[^\s<]+)",
        re.IGNORECASE,
    )
