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
                    title=xpath.first("@title"),
                    text=xpath.first("@text"),
                    rss=xpath.first(
                        "@xmlUrl",
                        converter=converters.url,
                        default=None,
                    ),
                    url=xpath.first(
                        "@htmlUrl",
                        converter=converters.url,
                        default=None,
                    ),
                )
    except lxml.etree.XMLSyntaxError as e:
        raise OpmlParserError from e
