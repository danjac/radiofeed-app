from __future__ import annotations

from typing import Generator

import attr
import lxml

from radiofeed.podcasts.parsers.rss_parser import url_or_none
from radiofeed.podcasts.parsers.xml_parser import XPathFinder, iterparse


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
                    title=finder.first("@title"),
                    rss=finder.first("@xmlUrl"),
                    url=finder.first("@htmlUrl"),
                    text=finder.first("@text"),
                )
                element.clear()
    except lxml.etree.XMLSyntaxError as e:
        raise OpmlParserError from e
