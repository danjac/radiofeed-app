import functools
from collections.abc import Iterator

import lxml.etree  # nosec

from radiofeed.feedparser.exceptions import InvalidRSSError
from radiofeed.feedparser.models import Feed, Item
from radiofeed.xml_parser import XMLParser


def parse_rss(content: bytes) -> Feed:
    """Parses RSS or Atom feed and returns the feed details and individual episodes.

    Args:
        content: the body of the RSS or Atom feed

    Raises:
        InvalidRSSError: if XML content is unparseable, or the feed is otherwise invalid
        or empty.
    """
    return _rss_parser().parse(content)


class RSSParser:
    """Parses RSS or Atom feed and returns the feed details and individual episodes."""

    def __init__(self):
        self._parser = XMLParser(
            {
                "atom": "http://www.w3.org/2005/Atom",
                "content": "http://purl.org/rss/1.0/modules/content/",
                "googleplay": "http://www.google.com/schemas/play-podcasts/1.0",
                "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
                "media": "http://search.yahoo.com/mrss/",
                "podcast": "https://podcastindex.org/namespace/1.0",
            }
        )

    def parse(self, content: bytes) -> Feed:
        """Parses RSS feed.

        Raises:
            InvalidRSSError: if XML content is unparseable, or the feed is otherwise invalid
            or empty.
        """
        try:
            return self._parse_feed(
                next(self._parser.iterparse(content, "rss", "channel"))
            )
        except StopIteration as e:
            msg = "Document does not contain <channel /> element"
            raise InvalidRSSError(msg) from e
        except lxml.etree.XMLSyntaxError as e:
            raise InvalidRSSError from e

    def _parse_feed(self, channel: lxml.etree.Element) -> Feed:
        """Parse a RSS XML feed."""
        try:
            return Feed(
                items=list(self._parse_items(channel)),
                categories=self._parser.aslist(
                    channel,
                    "//googleplay:category/@text",
                    "//itunes:category/@text",
                    "//media:category/@label",
                    "//media:category/text()",
                ),
                **self._parser.asdict(
                    channel,
                    complete="itunes:complete/text()",
                    cover_url=("itunes:image/@href", "image/url/text()"),
                    description=("description/text()", "itunes:summary/text()"),
                    explicit="itunes:explicit/text()",
                    funding_text="podcast:funding/text()",
                    funding_url="podcast:funding/@url",
                    language="language/text()",
                    website="link/text()",
                    owner=(
                        "itunes:author/text()",
                        "itunes:owner/itunes:name/text()",
                    ),
                    title="title/text()",  # type: ignore
                ),
            )
        except (TypeError, ValueError) as e:
            raise InvalidRSSError from e
        finally:
            channel.clear()

    def _parse_items(self, channel: lxml.etree.Element) -> Iterator[Item]:
        for item in self._parser.iterpaths(channel, "item"):
            try:
                yield Item(
                    categories=self._parser.aslist(item, "category/text()"),
                    **self._parser.asdict(
                        item,
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
                        website="link/text()",
                        media_type=("enclosure//@type", "media:content//@type"),
                        media_url=("enclosure//@url", "media:content//@url"),
                        pub_date=("pubDate/text()", "pubdate/text()"),
                        season="itunes:season/text()",
                        title="title/text()",  # type: ignore
                    ),
                )
            except (TypeError, ValueError):
                continue
            finally:
                item.clear()


@functools.cache
def _rss_parser() -> RSSParser:
    return RSSParser()
