from __future__ import annotations

import dataclasses

from typing import Generator

import lxml

from radiofeed.podcasts.parsers import converters, xml_parser


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
                    text=finder.first("@text"),
                    rss=converters.url(finder.first("@xmlUrl")),
                    url=converters.url(finder.first("@htmlUrl")),
                )
    except lxml.etree.XMLSyntaxError as e:
        raise OpmlParserError from e
