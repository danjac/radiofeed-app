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
            with xml_parser.xpath(element) as xpath:
                yield Outline(
                    title=converters.text(xpath("@title")),
                    text=converters.text(xpath("@text")),
                    rss=converters.url(xpath("@xmlUrl")),
                    url=converters.url(xpath("@xmlUrl")),
                )
    except lxml.etree.XMLSyntaxError as e:
        raise OpmlParserError from e
