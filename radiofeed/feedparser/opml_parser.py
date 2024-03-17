import functools
from collections.abc import Iterator

import lxml.etree

from radiofeed.feedparser.xpath_parser import XPathParser


def parse_opml(content: bytes) -> Iterator[str]:
    """Parse OPML document and return podcast URLs"""

    return _opml_parser().parse(content)


class OPMLParser:
    """Parse OPML document."""

    def __init__(self) -> None:
        self._parser = XPathParser()

    def parse(self, content: bytes) -> Iterator[str]:
        """Parse OPML content."""
        try:
            for element in self._parser.iterparse(content, "opml", "body"):
                yield from self._parser.itervalues(element, ".//outline/@xmlUrl")
        except lxml.etree.XMLSyntaxError:
            return


@functools.cache
def _opml_parser() -> OPMLParser:
    return OPMLParser()
