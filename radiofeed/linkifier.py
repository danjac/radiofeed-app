import dataclasses
import functools
import re
from collections.abc import Iterator
from typing import Final

import bs4
from bs4.element import Tag

_TRAILING_PUNCTUATION: Final = ",.;:!?)]}"


def linkify(content: str) -> str:
    """Converts URLs to links, if not already in <a> tags."""
    soup = bs4.BeautifulSoup(content, "html.parser")
    return _Linkifier(soup=soup).linkify()


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _UrlMatch:
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


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _Linkifier:
    soup: bs4.BeautifulSoup

    def linkify(self) -> str:
        for node in list(self.soup.find_all(string=True)):
            if not node.parent or node.parent.name == "a":
                continue

            if replacements := list(self._insert_links(str(node))):
                for replacement in replacements:
                    node.insert_before(replacement)
                node.extract()
        return str(self.soup)

    def _insert_links(self, text: str) -> Iterator[str | Tag]:
        """Yields text and link tags for the given text, replacing URLs with <a> tags."""
        last_index = 0
        for match in self._find_url_matches(text):
            if match.start > last_index:
                yield text[last_index : match.start]

            anchor = self.soup.new_tag("a", href=match.normalize_url())
            anchor.string = match.url
            yield anchor

            if match.trailing:
                yield match.trailing

            last_index = match.end

        if last_index < len(text):
            yield text[last_index:]

    def _find_url_matches(self, text: str) -> Iterator[_UrlMatch]:
        """Finds URLs in the given text and yields UrlMatch objects."""
        for match in _re_linkify_pattern().finditer(text):
            start, end = match.span()
            matched = match.group("url")

            if url := matched.rstrip(_TRAILING_PUNCTUATION):
                yield _UrlMatch(
                    start=start,
                    end=end,
                    url=url,
                    trailing=matched[len(url) :],
                )


@functools.cache
def _re_linkify_pattern() -> re.Pattern:
    return re.compile(r"(?P<url>(?:(?:https?|ftp)://|www\.)[^\s<]+)", re.IGNORECASE)
