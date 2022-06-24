import lxml

from radiofeed.podcasts.parsers import xml_parser
from radiofeed.podcasts.parsers.models import Outline


class OpmlParserError(ValueError):
    ...


def parse_opml(content):
    try:
        for element in xml_parser.iterparse(content, "outline"):
            with xml_parser.xpath(element) as xpath:
                try:
                    yield Outline(
                        title=xpath.first("@title"),
                        text=xpath.first("@text"),
                        rss=xpath.first("@xmlUrl"),
                        url=xpath.first("@xmlUrl"),
                    )
                except ValueError:
                    continue
    except lxml.etree.XMLSyntaxError as e:
        raise OpmlParserError from e
