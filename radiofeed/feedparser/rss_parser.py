import lxml.etree

from radiofeed.common.utils.xml import parse_xml, xpath_finder
from radiofeed.feedparser.exceptions import RssParserError
from radiofeed.feedparser.models import Feed, Item

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "media": "http://search.yahoo.com/mrss/",
    "podcast": "https://podcastindex.org/namespace/1.0",
}


def parse_rss(content):
    """Parses RSS or Atom feed and returns the feed details and individual episodes.

    Args:
        content (bytes): the body of the RSS or Atom feed

    Returns:
        Feed

    Raises:
        RssParserError: if XML content is invalid, or the feed is otherwise invalid or empty
    """
    try:
        return _parse_feed(next(parse_xml(content, "channel")))
    except (StopIteration, TypeError, ValueError, lxml.etree.XMLSyntaxError) as e:
        raise RssParserError from e


def _parse_feed(channel):
    with xpath_finder(channel, NAMESPACES) as finder:
        return Feed(
            title=finder.first("title/text()"),
            language=finder.first("language/text()"),
            complete=finder.first("itunes:complete/text()"),
            explicit=finder.first("itunes:explicit/text()"),
            cover_url=finder.first(
                "itunes:image/@href",
                "image/url/text()",
            ),
            link=finder.first("link/text()"),
            funding_url=finder.first("podcast:funding/@url"),
            funding_text=finder.first(
                "podcast:funding/text()",
            ),
            description=finder.first(
                "description/text()",
                "itunes:summary/text()",
            ),
            owner=finder.first(
                "itunes:author/text()",
                "itunes:owner/itunes:name/text()",
            ),
            categories=list(finder.iter("//itunes:category/@text")),
            items=list(_parse_items(channel)),
        )


def _parse_items(channel):
    for item in channel.iterfind("item"):
        try:
            yield _parse_item(item)
        except (TypeError, ValueError):
            continue


def _parse_item(item):
    with xpath_finder(item, NAMESPACES) as finder:
        return Item(
            guid=finder.first("guid/text()"),
            title=finder.first("title/text()"),
            pub_date=finder.first(
                "pubDate/text()",
                "pubdate/text()",
            ),
            media_url=finder.first(
                "enclosure//@url",
                "media:content//@url",
            ),
            media_type=finder.first(
                "enclosure//@type",
                "media:content//@type",
            ),
            cover_url=finder.first("itunes:image/@href"),
            link=finder.first("link/text()"),
            explicit=finder.first("itunes:explicit/text()"),
            duration=finder.first("itunes:duration/text()"),
            length=finder.first(
                "enclosure//@length",
                "media:content//@fileSize",
            ),
            episode=finder.first("itunes:episode/text()"),
            season=finder.first("itunes:season/text()"),
            episode_type=finder.first("itunes:episodetype/text()"),
            description=finder.first(
                "content:encoded/text()",
                "description/text()",
                "itunes:summary/text()",
            ),
            keywords=" ".join(finder.iter("category/text()")),
        )
