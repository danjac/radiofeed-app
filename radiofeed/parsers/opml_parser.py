import functools
from typing import TYPE_CHECKING

from radiofeed.parsers.xpath_parser import XPathParser

if TYPE_CHECKING:
    from collections.abc import Iterator


def parse_opml(content: bytes) -> Iterator[str]:
    """Parse OPML document and return podcast URLs"""

    return _opml_parser().parse(content)


class _OpmlParser:
    """Parse OPML document."""

    def __init__(self) -> None:
        self._parser = XPathParser()

    def parse(self, content: bytes) -> Iterator[str]:
        """Parse OPML content, returning RSS or Atom URLs."""
        yield from self._parser.itervalues(
            self._parser.find(content, "opml", "body"),
            ".//outline/@xmlUrl",
        )


@functools.cache
def _opml_parser() -> _OpmlParser:
    return _OpmlParser()
