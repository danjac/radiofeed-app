from __future__ import annotations

import dataclasses

from typing import Generator

import lxml

from radiofeed.podcasts.parsers import xml_parser
from radiofeed.podcasts.parsers.rss_parser import parse_url


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
        for element in xml_parser.iterparse(content, "outline"):
            with xml_parser.xpath_finder(element) as finder:
                yield Outline(
                    title=finder.first("@title"),
                    rss=parse_url(finder.first("@xmlUrl")),
                    url=parse_url(finder.first("@htmlUrl")),
                    text=finder.first("@text"),
                )
    except lxml.etree.XMLSyntaxError as e:
        raise OpmlParserError from e
