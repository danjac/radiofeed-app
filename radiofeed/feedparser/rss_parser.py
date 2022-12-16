from __future__ import annotations

from typing import Iterator

import lxml.etree  # nosec

from radiofeed.common.xml import XPathFinder
from radiofeed.feedparser.models import Feed, Item

_xpath_finder = XPathFinder(
    {
        "atom": "http://www.w3.org/2005/Atom",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "googleplay": "http://www.google.com/schemas/play-podcasts/1.0",
        "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "media": "http://search.yahoo.com/mrss/",
        "podcast": "https://podcastindex.org/namespace/1.0",
    }
)


class RssParserError(ValueError):
    """Broken XML syntax or missing/invalid required attributes."""


def parse_rss(content: bytes) -> Feed:
    """Parses RSS or Atom feed and returns the feed details and individual episodes.

    Args:
        content: the body of the RSS or Atom feed

    Raises:
        RssParserError: if XML content is unparseable, or the feed is otherwise invalid or empty
    """
    try:
        return _parse_feed(next(_xpath_finder.iterparse(content, "rss", "channel")))
    except StopIteration:
        raise RssParserError("Document does not contain <channel /> element")
    except lxml.etree.XMLSyntaxError as e:
        raise RssParserError from e


def _parse_feed(channel: lxml.etree.Element) -> Feed:
    """Parse a RSS XML feed."""
    try:
        return Feed(
            items=list(_parse_items(channel)),
            categories=_xpath_finder.aslist(
                channel,
                "//googleplay:category/@text",
                "//itunes:category/@text",
                "//media:category/@label",
                "//media:category/text()",
            ),
            **_xpath_finder.asdict(
                channel,
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
    finally:
        channel.clear()


def _parse_items(channel: lxml.etree.Element) -> Iterator[Item]:
    for item in _xpath_finder.findall(channel, "item"):
        try:
            yield Item(
                categories=_xpath_finder.aslist(item, "category/text()"),
                **_xpath_finder.asdict(
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
                    link="link/text()",
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
