from __future__ import annotations

import dataclasses

from typing import Generator

import lxml

from radiofeed.podcasts.parsers.rss_parser import parse_url
from radiofeed.podcasts.parsers.xml_parser import XPathFinder, iterparse


class OpmlParserError(ValueError):
    ...


@dataclasses.dataclass(frozen=True)
class Outline:

    title: str = ""
    text: str = ""
    rss: str | None = None
    url: str | None = None


def parse_opml(content: bytes) -> Generator[Outline, None, None]:
    try:
        for element in iterparse(content):
            if element.tag == "outline":
                finder = XPathFinder(element)
                yield Outline(
                    title=finder.first("@title"),
                    rss=parse_url(finder.first("@xmlUrl")),
                    url=parse_url(finder.first("@htmlUrl")),
                    text=finder.first("@text"),
                )
                element.clear()
    except lxml.etree.XMLSyntaxError as e:
        raise OpmlParserError from e
