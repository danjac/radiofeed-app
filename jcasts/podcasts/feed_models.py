from __future__ import annotations

import itertools

from datetime import datetime
from typing import Optional

from django.template.defaultfilters import striptags
from django.utils import timezone
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    ValidationError,
    root_validator,
    validator,
)

from jcasts.podcasts.date_parser import parse_date
from jcasts.podcasts.models import Podcast
from jcasts.shared.template.defaulttags import unescape


class ItunesResult(BaseModel):

    title: str = Field(alias="collectionName")
    rss: HttpUrl = Field(alias="feedUrl")
    itunes: HttpUrl = Field(alias="trackViewUrl")
    image: HttpUrl = Field(alias="artworkUrl600")

    podcast: Optional[Podcast] = None

    class Config:
        arbitrary_types_allowed = True

    def get_cleaned_title(self) -> str:
        return striptags(unescape(self.title))


class ContentItem(BaseModel):
    value: str = ""
    type: str = ""


class Link(BaseModel):
    href: HttpUrl
    length: Optional[int] = None
    type: str = ""
    rel: str = ""

    def is_audio(self) -> bool:
        return self.type.startswith("audio") and self.rel == "enclosure"


class Tag(BaseModel):
    term: str


class Author(BaseModel):
    name: str = ""


class Image(BaseModel):
    href: HttpUrl


class Item(BaseModel):

    id: str
    title: str

    published: datetime
    audio: Link

    link: str = ""
    image: Optional[Image] = None

    itunes_explicit: bool = False
    itunes_season: Optional[int] = None
    itunes_episode: Optional[int] = None
    itunes_episodetype: str = "full"
    itunes_duration: str = ""

    description: str = ""
    summary: str = ""

    content: list[ContentItem] = []
    enclosures: list[Link] = []
    links: list[Link] = []
    tags: list[Tag] = []

    @validator("published", pre=True)
    def get_published(cls, value: str | None) -> datetime | None:
        pub_date = parse_date(value)
        if pub_date and pub_date < timezone.now():
            return pub_date
        raise ValueError("no pub date")

    @validator("itunes_explicit", pre=True)
    def get_explicit(cls, value: str | bool | None) -> bool:
        return is_explicit(value)

    @root_validator(pre=True)
    def get_audio(cls, values: dict) -> dict:
        for value in itertools.chain(
            *[values.get(field, []) for field in ("links", "enclosures")]
        ):
            try:

                if not isinstance(value, Link):
                    value = Link(**value)

                if value.is_audio():
                    return {**values, "audio": value}

            except ValidationError:
                pass

        raise ValueError("audio missing")

    @root_validator
    def get_description_from_content(cls, values: dict) -> dict:
        content_items = values.get("content", [])

        for item in itertools.chain(
            *[
                [
                    item
                    for item in content_items
                    if item.value and item.type == content_type
                ]
                for content_type in ("text/html", "text/plain")
            ]
        ):
            return {**values, "description": item.value}
        return values


class Feed(BaseModel):

    title: str
    link: str = ""

    language: str = "en"

    image: Optional[Image] = None

    author: str = ""
    publisher_detail: Optional[Author] = None

    summary: str = ""
    description: str = ""
    subtitle: str = ""

    itunes_explicit: bool = False

    tags: list[Tag] = []

    @validator("itunes_explicit", pre=True)
    def get_explicit(cls, value: str | bool | None) -> bool:
        return is_explicit(value)

    @validator("language")
    def get_language(cls, value: str) -> str:
        return value[:2]


class Result(BaseModel):
    feed: Feed
    entries: list[Item]

    @validator("entries", pre=True)
    def get_items(cls, value: list) -> list:
        items = []
        for item in value:
            try:
                Item(**item)
            except ValidationError:
                pass
            else:
                items.append(item)
        if not items:
            raise ValueError("feed must have at least 1 item")
        return items


def is_explicit(value: str | bool | None):
    return value not in (False, None, "no", "none")
