from typing import Generator, List, Optional

import lxml

from lxml.etree import ElementBase
from pydantic import ValidationError

from .exceptions import InvalidFeedError
from .models import Audio, Feed, Item


def parse_feed(raw: bytes) -> Feed:

    if (
        rss := lxml.etree.fromstring(
            raw,
            parser=lxml.etree.XMLParser(
                strip_cdata=False,
                ns_clean=True,
                recover=True,
                encoding="utf-8",
            ),
        )
    ) is None:
        raise InvalidFeedError("No RSS content found")

    if (channel := rss.find("channel")) is None:
        raise InvalidFeedError("RSS does not contain <channel />")

    return FeedParser(channel).parse()


class RssParser:
    NAMESPACES = {
        "atom": "http://www.w3.org/2005/Atom",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "googleplay": "http://www.google.com/schemas/play-podcasts/1.0",
        "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "media": "http://search.yahoo.com/mrss/",
        "podcast": "https://podcastindex.org/namespace/1.0",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    }

    def __init__(self, tag: ElementBase):
        self.tag = tag

    def parse_tag(self, xpath: str) -> Optional[ElementBase]:
        return self.tag.find(xpath, self.NAMESPACES)

    def parse_tags(self, xpath: str) -> List[ElementBase]:
        return self.tag.findall(xpath, self.NAMESPACES)

    def parse_attribute(self, xpath: str, attr: str) -> Optional[str]:
        if (tag := self.parse_tag(xpath)) is None:
            return None
        try:
            return tag.attrib[attr]
        except KeyError:
            return None

    def parse_attribute_list(self, xpath: str, attr: str) -> List[str]:
        return [
            (tag.attrib[attr] or "")
            for tag in self.parse_tags(xpath)
            if attr in tag.attrib
        ]

    def parse_text(self, xpath: str) -> str:
        if (tag := self.parse_tag(xpath)) is None:
            return ""
        return tag.text or ""

    def parse_text_list(self, xpath: str) -> List[str]:
        return [(item.text or "") for item in self.parse_tags(xpath)]

    def parse_explicit(self) -> bool:
        return self.parse_text("itunes:explicit").lower() == "yes"


class FeedParser(RssParser):
    def parse(self) -> Feed:
        return Feed(
            title=self.parse_text("title"),
            link=self.parse_text("link"),
            categories=self.parse_attribute_list(".//itunes:category", "text"),
            creators=set(self.parse_creators()),
            image=self.parse_image(),
            description=self.parse_description(),
            explicit=self.parse_explicit(),
            items=list(self.parse_items()),
        )

    def parse_image(self) -> Optional[str]:
        return (
            self.parse_attribute("itunes:image", "href")
            or self.parse_text("image/url")
            or self.parse_attribute("googleplay:image", "href")
        )

    def parse_description(self) -> str:
        return (
            self.parse_text("description")
            or self.parse_text("googleplay:description")
            or self.parse_text("itunes:summary")
            or self.parse_text("itunes:subtitle")
        )

    def parse_creators(self) -> List[str]:
        return self.parse_text_list("itunes:owner/itunes:name") + self.parse_text_list(
            "itunes:author"
        )

    def parse_items(self) -> Generator:

        guids = set()

        for parser in [ItemParser(tag) for tag in self.parse_tags("item")]:
            try:
                item = parser.parse()
                if item.guid not in guids:
                    yield item
                guids.add(item.guid)
            except ValidationError:
                pass


class ItemParser(RssParser):
    def parse(self) -> Item:
        return Item(
            guid=self.parse_guid(),
            title=self.parse_text("title"),
            duration=self.parse_text("itunes:duration"),
            link=self.parse_text("link"),
            pub_date=self.parse_text("pubDate"),
            explicit=self.parse_explicit(),
            audio=self.parse_audio(),
            description=self.parse_description(),
            keywords=self.parse_keywords(),
        )

    def parse_guid(self) -> str:
        return self.parse_text("guid") or self.parse_text("itunes:episode")

    def parse_audio(self) -> Optional[Audio]:

        if (enclosure := self.parse_tag("enclosure")) is None:
            return None

        return Audio(
            length=enclosure.attrib.get("length"),
            url=enclosure.attrib.get("url"),
            type=enclosure.attrib.get("type"),
        )

    def parse_description(self) -> str:

        return (
            self.parse_text("content:encoded")
            or self.parse_text("description")
            or self.parse_text("googleplay:description")
            or self.parse_text("itunes:summary")
            or self.parse_text("itunes:subtitle")
        )

    def parse_keywords(self) -> str:
        rv = self.parse_text_list("category")
        if (keywords := self.parse_text("itunes:keywords")) :
            rv.append(keywords)
        return " ".join(rv)
