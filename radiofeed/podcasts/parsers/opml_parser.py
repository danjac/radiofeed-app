import attrs
import lxml

from radiofeed.podcasts.parsers import xml_parser
from radiofeed.podcasts.parsers.rss_parser import url


@attrs.define(kw_only=True, frozen=True)
class Outline:

    title: str = attrs.field(
        converter=attrs.converters.default_if_none(""),
        default=None,
    )

    text: str = attrs.field(
        converter=attrs.converters.default_if_none(""),
        default=None,
    )

    rss: str = attrs.field(validator=url)

    url: str | None = attrs.field(
        validator=attrs.validators.optional(url),
        default=None,
    )


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
