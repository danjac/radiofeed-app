import functools
from collections.abc import Iterator
from typing import IO

import lxml

from radiofeed.xml_parser import XMLParser


def parse_opml(fp: IO) -> Iterator[str]:
    """Parse OPML document and return podcast URLs"""
    parser = _opml_parser()
    try:
        for element in parser.iterparse(fp.read(), "opml", "body"):
            try:
                yield from parser.itertext(element, "//outline//@xmlUrl")
            finally:
                element.clear()
    except lxml.etree.XMLSyntaxError:
        return


@functools.cache
def _opml_parser() -> XMLParser:
    """Returns cached XMLParser instance."""
    return XMLParser()
