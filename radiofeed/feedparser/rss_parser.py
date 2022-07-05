import lxml.etree

from radiofeed.common.utils.xml import parse_xml, xpath_finder
from radiofeed.feedparser.exceptions import RssParserError
from radiofeed.feedparser.models import Feed, Item

_namespaces = {
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
    with xpath_finder(channel, _namespaces) as finder:
        return Feed(
            categories=list(finder.iter("//itunes:category/@text")),
            items=list(_parse_items(channel)),
            **finder.to_dict(
                title="title/text()",
                language="language/text()",
                complete="itunes:complete/text()",
                explicit="itunes:explicit/text()",
                cover_url=(
                    "itunes:image/@href",
                    "image/url/text()",
                ),
                link="link/text()",
                funding_url="podcast:funding/@url",
                funding_text="podcast:funding/text()",
                description=(
                    "description/text()",
                    "itunes:summary/text()",
                ),
                owner=(
                    "itunes:author/text()",
                    "itunes:owner/itunes:name/text()",
                ),
            ),
        )


def _parse_items(channel):
    for item in channel.iterfind("item"):
        try:
            yield _parse_item(item)
        except (TypeError, ValueError):
            continue


def _parse_item(item):
    with xpath_finder(item, _namespaces) as finder:
        return Item(
            keywords=" ".join(finder.iter("category/text()")),
            **finder.to_dict(
                guid="guid/text()",
                title="title/text()",
                pub_date=(
                    "pubDate/text()",
                    "pubdate/text()",
                ),
                media_url=(
                    "enclosure//@url",
                    "media:content//@url",
                ),
                media_type=(
                    "enclosure//@type",
                    "media:content//@type",
                ),
                cover_url="itunes:image/@href",
                link="link/text()",
                explicit="itunes:explicit/text()",
                duration="itunes:duration/text()",
                length=(
                    "enclosure//@length",
                    "media:content//@fileSize",
                ),
                episode="itunes:episode/text()",
                season="itunes:season/text()",
                episode_type="itunes:episodetype/text()",
                description=(
                    "content:encoded/text()",
                    "description/text()",
                    "itunes:summary/text()",
                ),
            ),
        )
