from __future__ import annotations

import dataclasses
import mimetypes

from datetime import datetime
from typing import Generator

import lxml

from django.core.validators import (
    MaxLengthValidator,
    RegexValidator,
    URLValidator,
    ValidationError,
)
from django.utils import timezone
from lxml.etree import ElementBase, XMLSyntaxError

from audiotrails.podcasts.date_parser import parse_date


@dataclasses.dataclass
class Audio:

    type: str
    url: str
    length: int | None = None
    rel: str = ""

    def __post_init__(self) -> None:
        _validate_url(self.url)
        _validate_audio_type(self.type)
        _validate_audio_type_length(self.type)


@dataclasses.dataclass
class Item:
    audio: Audio | None

    title: str
    guid: str
    duration: str

    raw_pub_date: str

    explicit: bool = False
    description: str = ""

    link: str = ""
    keywords: str = ""

    pub_date: datetime | None = None

    def __post_init__(self) -> None:
        if (pub_date := parse_date(self.raw_pub_date)) is None:
            raise ValidationError("missing or invalid date")

        if self.audio is None:
            raise ValidationError("missing audio")

        _validate_duration_length(self.duration)

        self.pub_date = pub_date
        self.link = _clean_url(self.link)


@dataclasses.dataclass
class Feed:
    title: str
    description: str
    creators: set[str]
    image: str | None
    categories: list[str]
    items: list[Item]

    explicit: bool = False

    language: str = "en"
    link: str = ""

    def __post_init__(self) -> None:
        if len(self.items) == 0:
            raise ValidationError("Must be at least one item")

        self.link = _clean_url(self.link)

        self.language = (
            self.language.replace("-", "").strip()[:2] if self.language else "en"
        ).lower()

    def get_creators(self) -> str:
        return ", ".join(
            {
                c
                for c in {
                    c.lower(): c for c in [c.strip() for c in self.creators]
                }.values()
                if c
            }
        )

    def get_pub_date(self) -> datetime | None:
        now = timezone.now()
        try:
            return max(item.pub_date for item in self.items if item.pub_date < now)
        except ValueError:
            return None


def _clean_url(url: str | None) -> str:

    if not url:
        return ""

    # links often just consist of domain: try prefixing http://
    if not url.startswith("http"):
        url = "http://" + url

    # if not a valid URL, just make empty string
    try:
        _validate_url(url)
        _validate_url_length(url)
    except (TypeError, ValidationError):
        return ""

    return url


class RssParserError(ValueError):
    ...


def parse_feed(raw: bytes) -> Feed:

    try:
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
            raise RssParserError("No RSS content found")
        if (channel := rss.find("channel")) is None:
            raise RssParserError("RSS does not contain <channel />")

        return FeedParser(channel).parse()
    except (
        ValidationError,
        XMLSyntaxError,
    ) as e:
        raise RssParserError from e


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

    def parse_tag(self, xpath: str) -> ElementBase | None:
        return self.tag.find(xpath, self.NAMESPACES)

    def parse_tags(self, xpath: str) -> list[ElementBase]:
        return self.tag.findall(xpath, self.NAMESPACES)

    def parse_attribute(self, xpath: str, attr: str) -> str | None:
        if (tag := self.parse_tag(xpath)) is None:
            return None
        try:
            return tag.attrib[attr]
        except KeyError:
            return None

    def parse_attribute_list(self, xpath: str, attr: str) -> list[str]:
        return [
            (tag.attrib[attr] or "")
            for tag in self.parse_tags(xpath)
            if attr in tag.attrib
        ]

    def parse_text(self, xpath):
        if (tag := self.parse_tag(xpath)) is None:
            return ""
        return tag.text or ""

    def parse_text_list(self, xpath):
        return [(item.text or "") for item in self.parse_tags(xpath)]

    def parse_explicit(self):
        return self.parse_text("itunes:explicit").lower() == "yes"


class FeedParser(RssParser):
    def parse(self) -> Feed:
        return Feed(
            title=self.parse_text("title"),
            language=self.parse_text("language"),
            link=self.parse_text("link"),
            categories=self.parse_attribute_list(".//itunes:category", "text"),
            creators=set(self.parse_creators()),
            image=self.parse_image(),
            description=self.parse_description(),
            explicit=self.parse_explicit(),
            items=list(self.parse_items()),
        )

    def parse_image(self) -> str | None:
        return (
            self.parse_attribute("itunes:image", "href")
            or self.parse_text("image/url")
            or self.parse_attribute("googleplay:image", "href")
        )

    def parse_description(self) -> str | None:
        return (
            self.parse_text("description")
            or self.parse_text("googleplay:description")
            or self.parse_text("itunes:summary")
            or self.parse_text("itunes:subtitle")
        )

    def parse_creators(self) -> list[str]:
        return self.parse_text_list("itunes:owner/itunes:name") + self.parse_text_list(
            "itunes:author"
        )

    def parse_items(self) -> Generator[Item, None, None]:

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
            raw_pub_date=self.parse_text("pubDate"),
            explicit=self.parse_explicit(),
            audio=self.parse_audio(),
            description=self.parse_description(),
            keywords=self.parse_keywords(),
        )

    def parse_guid(self) -> str:
        return self.parse_text("guid") or self.parse_text("itunes:episode")

    def parse_audio(self) -> Audio | None:

        if (enclosure := self.parse_tag("enclosure")) is None:
            return None

        url = enclosure.attrib.get("url")

        if not (media_type := enclosure.attrib.get("type")):
            media_type, _ = mimetypes.guess_type(url)

        if length := enclosure.attrib.get("length"):
            try:
                length = round(float(length.replace(",", "")))
            except ValueError:
                length = None

        return Audio(length=length, type=media_type, url=url)

    def parse_description(self) -> str:

        for tagname in (
            "content:encoded",
            "description",
            "googleplay:description",
            "itunes:summary",
            "itunes:subtitle",
        ):
            if value := self.parse_text(tagname).strip():
                return value

        return ""

    def parse_keywords(self) -> str:
        rv = self.parse_text_list("category")
        if keywords := self.parse_text("itunes:keywords"):
            rv.append(keywords)
        return " ".join(rv)


# validators

_validate_audio_type_length = MaxLengthValidator(60)
_validate_audio_type = RegexValidator(r"^audio/*")
_validate_duration_length = MaxLengthValidator(30)
_validate_url_length = MaxLengthValidator(500)
_validate_url = URLValidator(schemes=["http", "https"])
