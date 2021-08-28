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


def parse_rss(content):

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

    raise RssParserError("<channel /> not found in RSS feed")


def parse_channel(channel):
    try:
        feed = Feed.parse_obj(parse_feed(channel))
    except ValidationError as e:
        raise RssParserError from e
    if not (items := [*parse_items(channel)]):
        raise RssParserError("no items found in RSS feed")
    return feed, items


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


def parse_feed(channel):
    return {
        "title": xfind(channel, "title/text()"),
        "link": xfind(channel, "link/text()", default=""),
        "language": xfind(channel, "language/text()", default="en"),
        "explicit": xfind(channel, "itunes:explicit/text()"),
        "cover_url": xfind(channel, "itunes:image/@href", "image/url/text()"),
        "description": xfind(
            channel, "description/text()", "itunes:summary/text()", default=""
        ),
        "owner": xfind(
            channel,
            "itunes:author/text()",
            "itunes:owner/itunes:name/text()",
            default="",
        ),
        "categories": xfindall(channel, "//itunes:category/@text"),
    }


def parse_items(channel):

    for item in channel.iterfind("item"):

        try:
            yield Item.parse_obj(parse_item(item))

        except ValidationError:
            ...


def parse_item(item):
    return {
        "guid": xfind(item, "guid/text()"),
        "title": xfind(item, "title/text()"),
        "pub_date": xfind(item, "pubDate/text()"),
        "media_url": xfind(item, "enclosure//@url"),
        "media_type": xfind(item, "enclosure//@type"),
        "length": xfind(item, "enclosure//@length"),
        "cover_url": xfind(item, "itunes:image/@href"),
        "explicit": xfind(item, "itunes:explicit/text()"),
        "episode": xfind(item, "itunes:episode/text()"),
        "season": xfind(item, "itunes:season/text()"),
        "description": xfind(
            item,
            "content:encoded/text()",
            "description/text()",
            "itunes:summary/text()",
            default="",
        ),
        "duration": xfind(item, "itunes:duration/text()", default=""),
        "episode_type": xfind(item, "itunes:episodetype/text()", default="full"),
        "keywords": xfindall(item, "category/text()"),
    }


def xfind(element, *paths, default=None):
    for path in paths:
        if values := element.xpath(path, namespaces=NAMESPACES):
            return values[0].strip()
    return default


def xfindall(element, path):
    return [value.strip() for value in element.xpath(path, namespaces=NAMESPACES)]
