from collections.abc import Iterator
from typing import IO

import lxml

from radiofeed.feedparser.xpath_parser import XPathParser


def parse_opml(fp: IO) -> Iterator[str]:
    """Parse OPML document and return podcast URLs"""

    parser = _xpath_parser()
    try:
        for element in parser.iterparse(fp.read(), "opml", "body"):
            yield from parser.iterstrings(element, ".//outline/@xmlUrl")
    except lxml.etree.XMLSyntaxError:
        return


def _xpath_parser() -> XPathParser:
    return XPathParser()
