import io

from datetime import datetime
from typing import Optional

import lxml

from django.utils import timezone
from pydantic import BaseModel, HttpUrl, ValidationError, validator

from jcasts.podcasts.date_parser import parse_date

NAMESPACES = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
}


class RssParserError(ValueError):
    ...


class Item(BaseModel):

    guid: str
    title: str

    pub_date: datetime

    cover_url: Optional[HttpUrl] = None

    media_url: HttpUrl
    media_type: str = ""
    length: Optional[int] = None

    explicit: bool = False

    season: Optional[int] = None
    episode: Optional[int] = None

    episode_type: str = "full"
    duration: str = ""

    description: str = ""
    keywords: str = ""

    @validator("pub_date", pre=True)
    def get_pub_date(cls, value):
        pub_date = parse_date(value)
        if pub_date and pub_date < timezone.now():
            return pub_date
        raise ValueError("not a valid pub date")

    @validator("explicit", pre=True)
    def is_explicit(cls, value):
        return value.lower() in ("yes", "clean") if value else False

    @validator("keywords", pre=True)
    def get_keywords(cls, value):
        return " ".join(value)

    @validator("media_type")
    def is_audio(cls, value):
        if not (value or "").startswith("audio/"):
            raise ValueError("not a valid audio enclosure")
        return value


class Feed(BaseModel):

    title: str
    link: str

    language: str = "en"

    cover_url: Optional[HttpUrl] = None

    owner: str = ""
    description: str = ""

    explicit: bool = False

    categories: list[str] = []

    @validator("explicit", pre=True)
    def is_explicit(cls, value):
        return value.lower() in ("yes", "clean") if value else False

    @validator("language", pre=True)
    def get_language(cls, value):
        return value[:2]


def parse_rss(content):

    try:
        for _, element in lxml.etree.iterparse(
            io.BytesIO(content),
            encoding="utf-8",
            no_network=True,
            resolve_entities=False,
            recover=True,
            events=("end",),
        ):
            if element.tag == "channel":
                try:
                    return parse_channel(element)
                finally:
                    element.clear()

    except lxml.etree.XMLSyntaxError as e:
        raise RssParserError from e

    raise RssParserError("<channel /> not found in RSS feed")


def parse_channel(channel):
    try:
        feed = Feed.parse_obj(parse_feed(XPathFinder(channel, namespaces=NAMESPACES)))
    except ValidationError as e:
        raise RssParserError from e
    if not (items := [*parse_items(channel)]):
        raise RssParserError("no items found in RSS feed")
    return feed, items


def parse_feed(finder):
    return {
        "title": finder.find("title/text()"),
        "link": finder.find("link/text()", default=""),
        "language": finder.find("language/text()", default="en"),
        "explicit": finder.find("itunes:explicit/text()"),
        "cover_url": finder.find("itunes:image/@href", "image/url/text()"),
        "description": finder.find(
            "description/text()", "itunes:summary/text()", default=""
        ),
        "owner": finder.find(
            "itunes:author/text()",
            "itunes:owner/itunes:name/text()",
            default="",
        ),
        "categories": finder.findall("//itunes:category/@text"),
    }


def parse_items(channel):

    for item in channel.iterfind("item"):

        try:
            yield Item.parse_obj(parse_item(XPathFinder(item, namespaces=NAMESPACES)))

        except ValidationError:
            pass


def parse_item(finder):
    return {
        "guid": finder.find("guid/text()"),
        "title": finder.find("title/text()"),
        "pub_date": finder.find("pubDate/text()"),
        "media_url": finder.find("enclosure//@url"),
        "media_type": finder.find("enclosure//@type"),
        "length": finder.find("enclosure//@length"),
        "cover_url": finder.find("itunes:image/@href"),
        "explicit": finder.find("itunes:explicit/text()"),
        "episode": finder.find("itunes:episode/text()"),
        "season": finder.find("itunes:season/text()"),
        "description": finder.find(
            "content:encoded/text()",
            "description/text()",
            "itunes:summary/text()",
            default="",
        ),
        "duration": finder.find("itunes:duration/text()", default=""),
        "episode_type": finder.find("itunes:episodetype/text()", default="full"),
        "keywords": finder.findall("category/text()"),
    }


class XPathFinder:
    def __init__(self, element, namespaces=None):
        self.element = element
        self.namespaces = namespaces

    def find(self, *paths, default=None):

        """Find single attribute or text value. Returns
        first matching value."""
        for path in paths:
            try:
                if values := self.xpath(path):
                    return values[0].strip()
            except UnicodeDecodeError:
                pass
        return default

    def findall(self, path):
        """Returns list of attributes or text values"""
        try:
            return [value.strip() for value in self.xpath(path)]
        except UnicodeDecodeError:  # pragma: no cover
            return []

    def xpath(self, path):
        return self.element.xpath(path, namespaces=self.namespaces)
