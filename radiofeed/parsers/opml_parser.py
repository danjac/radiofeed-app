from __future__ import annotations

from typing import Generator

import attr
import lxml

from radiofeed.parsers.rss_parser import url_or_none
from radiofeed.parsers.xml_parser import XPathFinder, iterparse


class OpmlParserError(ValueError):
    ...


@attr.s(kw_only=True)
class Outline:

    title: str | None = attr.ib(default="")
    text: str = attr.ib(default="")
    rss: str | None = attr.ib(default=None, converter=url_or_none)
    url: str | None = attr.ib(default=None, converter=url_or_none)


def parse_opml(content: bytes) -> Generator[Outline, None, None]:
    try:
        for element in iterparse(content):
            if element.tag == "outline":
                finder = XPathFinder(element)
                yield Outline(
                    title=finder.find("@title"),
                    rss=finder.find("@xmlUrl"),
                    url=finder.find("@htmlUrl"),
                    text=finder.find("@text"),
                )
                element.clear()
    except lxml.etree.XMLSyntaxError as e:
        raise OpmlParserError from e
