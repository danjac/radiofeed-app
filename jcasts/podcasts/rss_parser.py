from __future__ import annotations

from datetime import datetime
from typing import Optional

import lxml

from django.utils import timezone
from pydantic import BaseModel, HttpUrl, ValidationError, validator

from jcasts.podcasts.date_parser import parse_date

NAMESPACES = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}


class RssParserError(ValueError):
    ...


class Item(BaseModel):

    guid: str
    title: str
    link: str = ""

    pub_date: datetime

    cover_url: Optional[HttpUrl]

    media_url: HttpUrl
    media_type: str
    length: Optional[int] = None

    explicit: bool = False

    season: Optional[int] = None
    episode: Optional[int] = None
    episode_type: str = "full"
    duration: str = ""

    description: str = ""
    keywords: str = ""

    @validator("pub_date", pre=True)
    def get_pub_date(cls, value: str | None) -> datetime | None:
        pub_date = parse_date(value)
        if pub_date and pub_date < timezone.now():
            return pub_date
        raise ValueError("not a valid pub date")

    @validator("explicit", pre=True)
    def is_explicit(cls, value: str) -> bool:
        return value.lower() in ("yes", "clean") if value else False

    @validator("keywords", pre=True)
    def get_keywords(cls, value: list) -> str:
        return " ".join(value)

    @validator("media_type")
    def is_audio(cls, value: str) -> str:
        if not (value or "").startswith("audio/"):
            raise ValueError("not a valid audio enclosure")
        return value


class Feed(BaseModel):

    title: str
    link: str = ""

    language: str = "en"
    cover_url: Optional[HttpUrl]

    owner: str = ""
    description: str = ""

    explicit: bool = False

    categories: list[str] = []

    @validator("explicit", pre=True)
    def is_explicit(cls, value: str) -> bool:
        return value.lower() in ("yes", "clean") if value else False

    @validator("language")
    def get_language(cls, value: str) -> str:
        return value[:2]


class XPathParser:
    def __init__(self, *paths: str, multiple: bool = False, default=None):
        self.paths = paths
        self.multiple = multiple
        self.default = default

    def parse(self, element: lxml.etree.Element) -> str | list:
        for path in self.paths:
            if value := element.xpath(path, namespaces=NAMESPACES):
                return value if self.multiple else value[0]
        return [] if self.multiple else self.default


ITEM_MAPPINGS = {
    "guid": XPathParser("guid/text()"),
    "title": XPathParser("title/text()"),
    "link": XPathParser("link/text()", default=""),
    "description": XPathParser("description/text()", default=""),
    "pub_date": XPathParser("pubDate/text()"),
    "media_url": XPathParser("enclosure//@url"),
    "media_type": XPathParser("enclosure//@type"),
    "length": XPathParser("enclosure//@length"),
    "cover_url": XPathParser("itunes:image/@href"),
    "explicit": XPathParser("itunes:explicit/text()"),
    "episode": XPathParser("itunes:episode/text()"),
    "season": XPathParser("itunes:season/text()"),
    "duration": XPathParser("itunes:duration/text()", default=""),
    "episode_type": XPathParser("itunes:episodetype/text()", default="full"),
    "keywords": XPathParser("category/text()", multiple=True),
}

FEED_MAPPINGS = {
    "title": XPathParser("title/text()"),
    "link": XPathParser("link/text()", default=""),
    "language": XPathParser("language/text()", default="en"),
    "description": XPathParser("description/text()", default=""),
    "cover_url": XPathParser("image/url/text()"),
    "explicit": XPathParser("itunes:explicit/text()"),
    "owner": XPathParser(
        "itunes:author/text()",
        "itunes:owner/itunes:name/text()",
    ),
    "categories": XPathParser("//itunes:category/@text", multiple=True),
}


def parse(element: lxml.etree.Element, mappings: dict[str, XPathParser]) -> dict:
    parsed = {}
    for field, parser in mappings.items():
        parsed[field] = parser.parse(element)
    return parsed


def parse_rss(content: bytes) -> tuple[Feed, list[Item]]:
    try:
        xml = lxml.etree.fromstring(content)
    except lxml.etree.XMLSyntaxError as e:
        raise RssParserError from e

    if (channel := xml.find("channel")) is None:
        raise RssParserError("<channel /> not found")

    try:
        feed = Feed.parse_obj(parse(channel, FEED_MAPPINGS))
    except ValidationError as e:
        raise RssParserError from e

    items = [
        item
        for item in [parse_item(element) for element in channel.iterfind("item")]
        if item
    ]
    if not items:
        raise RssParserError("no valid entries found")

    return feed, items


def parse_item(element: lxml.etree.Element) -> Item | None:

    try:
        return Item.parse_obj(parse(element, ITEM_MAPPINGS))
    except ValidationError:
        return None
