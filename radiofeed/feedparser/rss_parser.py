from typing import Generator

import lxml.etree

from radiofeed.common.utils.xml import parse_xml, xpath_finder
from radiofeed.feedparser.exceptions import RssParserError
from radiofeed.feedparser.models import Feed, Item


def parse_rss(content: bytes) -> Feed:
    """Parses RSS or Atom feed and returns the feed details and individual episodes.

    Args:
        content: the body of the RSS or Atom feed

    Raises:
        RssParserError: if XML content is invalid, or the feed is otherwise invalid or empty
    """
    try:
        return RssParser(next(parse_xml(content, "channel"))).parse()
    except (StopIteration, lxml.etree.XMLSyntaxError) as e:
        raise RssParserError from e


class RssParser:
    """Parses RSS or Atom field on <channel /> element.

    Args:
        channel (lxml.etree.Element): <channel /> element
    """

    _namespaces = {
        "atom": "http://www.w3.org/2005/Atom",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "media": "http://search.yahoo.com/mrss/",
        "podcast": "https://podcastindex.org/namespace/1.0",
    }

    def __init__(self, channel: lxml.etree.Element):
        self._channel = channel

    def parse(self) -> Feed:
        """Parses RSS into a Feed instance.

        Raises:
            RssParserError: missing or invalid RSS content
        """
        with xpath_finder(self._channel, self._namespaces) as finder:
            try:
                return Feed(
                    categories=list(finder.iter("//itunes:category/@text")),
                    items=list(self._parse_items()),
                    **finder.to_dict(
                        complete="itunes:complete/text()",
                        cover_url=("itunes:image/@href", "image/url/text()"),
                        description=("description/text()", "itunes:summary/text()"),
                        explicit="itunes:explicit/text()",
                        funding_text="podcast:funding/text()",
                        funding_url="podcast:funding/@url",
                        language="language/text()",
                        link="link/text()",
                        owner=(
                            "itunes:author/text()",
                            "itunes:owner/itunes:name/text()",
                        ),
                        title="title/text()",  # type: ignore
                    ),
                )
            except (TypeError, ValueError) as e:
                raise RssParserError from e

    def _parse_item(self, item: Item) -> Item:
        with xpath_finder(item, self._namespaces) as finder:
            return Item(
                categories=list(finder.iter("category/text()")),
                **finder.to_dict(
                    cover_url="itunes:image/@href",
                    description=(
                        "content:encoded/text()",
                        "description/text()",
                        "itunes:summary/text()",
                    ),
                    duration="itunes:duration/text()",
                    episode="itunes:episode/text()",
                    episode_type="itunes:episodetype/text()",
                    explicit="itunes:explicit/text()",
                    guid="guid/text()",
                    length=("enclosure//@length", "media:content//@fileSize"),
                    link="link/text()",
                    media_type=("enclosure//@type", "media:content//@type"),
                    media_url=("enclosure//@url", "media:content//@url"),
                    pub_date=("pubDate/text()", "pubdate/text()"),
                    season="itunes:season/text()",
                    title="title/text()",  # type: ignore
                ),
            )

    def _parse_items(self) -> Generator[Item, None, None]:
        for item in self._channel.iterfind("item"):
            try:
                yield self._parse_item(item)
            except (TypeError, ValueError):
                continue
