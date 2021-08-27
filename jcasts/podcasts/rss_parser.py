import io

from datetime import datetime
from typing import Optional

import lxml

from django.utils import timezone
from pydantic import BaseModel, HttpUrl, ValidationError, validator

from jcasts.podcasts.date_parser import parse_date


class RssParserError(ValueError):
    ...


def parse_rss(content):

    try:
        xml = lxml.etree.parse(
            io.BytesIO(content),
            parser=lxml.etree.XMLParser(
                encoding="utf-8",
                no_network=True,
                resolve_entities=False,
                recover=True,
            ),
        )
    except lxml.etree.XMLSyntaxError as e:
        raise RssParserError from e

    try:
        channel = xml.find("channel")
        assert channel is not None
    except AssertionError:
        raise RssParserError("<channel /> is missing")

    try:
        feed = Feed.parse_obj(FeedMapper().parse(channel))
    except ValidationError as e:
        raise RssParserError from e

    if not (items := [*parse_items(channel, ItemMapper())]):
        raise RssParserError("no valid entries found")

    return feed, items


def parse_items(channel, mapper):

    for element in channel.iterfind("item"):

        try:
            yield Item.parse_obj(mapper.parse(element))

        except ValidationError:
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


class XPathParser:
    def __init__(self, *paths, multiple=False, default=None):
        self.paths = paths
        self.multiple = multiple
        self.default = default

    def parse(self, element, namespaces):
        for path in self.paths:
            if value := list(
                map(
                    self.strip_whitespace,
                    element.xpath(path, namespaces=namespaces),
                )
            ):
                return value if self.multiple else value[0]

        return [] if self.multiple else self.default

    def strip_whitespace(self, value):
        return (value or "").strip()


class XPathMapper:
    mappings = {}

    namespaces = {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    }

    def parse(self, element):
        parsed = {}
        for field, parser in self.mappings.items():
            parsed[field] = parser.parse(element, self.namespaces)
        return parsed


class FeedMapper(XPathMapper):
    mappings = {
        "title": XPathParser("title/text()"),
        "link": XPathParser("link/text()", default=""),
        "language": XPathParser("language/text()", default="en"),
        "description": XPathParser(
            "description/text()",
            "itunes:summary/text()",
            default="",
        ),
        "cover_url": XPathParser(
            "itunes:image/@href",
            "image/url/text()",
        ),
        "owner": XPathParser(
            "itunes:author/text()", "itunes:owner/itunes:name/text()", default=""
        ),
        "explicit": XPathParser("itunes:explicit/text()"),
        "categories": XPathParser("//itunes:category/@text", multiple=True),
    }


class ItemMapper(XPathMapper):

    mappings = {
        "guid": XPathParser("guid/text()"),
        "title": XPathParser("title/text()"),
        "pub_date": XPathParser("pubDate/text()"),
        "media_url": XPathParser("enclosure//@url"),
        "media_type": XPathParser("enclosure//@type"),
        "length": XPathParser("enclosure//@length"),
        "cover_url": XPathParser("itunes:image/@href"),
        "explicit": XPathParser("itunes:explicit/text()"),
        "episode": XPathParser("itunes:episode/text()"),
        "season": XPathParser("itunes:season/text()"),
        "description": XPathParser(
            "content:encoded/text()",
            "description/text()",
            "itunes:summary/text()",
            default="",
        ),
        "duration": XPathParser("itunes:duration/text()", default=""),
        "episode_type": XPathParser("itunes:episodetype/text()", default="full"),
        "keywords": XPathParser("category/text()", multiple=True),
    }
