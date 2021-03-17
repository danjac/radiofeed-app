import datetime

from typing import List, Optional, Set

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from pydantic import BaseModel, HttpUrl, conlist, constr, validator

from .date_parser import parse_date


class Audio(BaseModel):
    type: constr(max_length=60)  # type: ignore
    url: HttpUrl
    length: Optional[int]

    @validator("type")
    def is_audio(cls, value: str) -> str:
        if not value.startswith("audio/"):
            raise ValueError("not a valid audio media")

        return value


class Item(BaseModel):
    audio: Audio
    title: str
    guid: str
    explicit: bool = False
    description: str = ""
    keywords: str = ""
    pub_date: datetime.datetime
    duration: constr(max_length=30)  # type: ignore

    @validator("pub_date", pre=True)
    def parse_date(cls, value: Optional[str]) -> datetime.datetime:
        if (pub_date := parse_date(value)) is None:
            raise ValueError("missing or invalid date")
        return pub_date


class Feed(BaseModel):
    title: str
    description: str
    explicit: bool = False
    language: str = "en"
    link: constr(max_length=500) = ""  # type: ignore
    items: conlist(Item, min_items=1)  # type: ignore
    authors: Set[str]
    image: Optional[str]
    categories: List[str]

    @validator("language")
    def language_code(cls, value: str) -> str:
        return (value[:2] if value else "en").strip().lower()

    @validator("link", pre=True)
    def prepare_link(cls, value: str) -> str:
        if not value:
            return value

        # links often just consist of domain: try prefixing http://
        if not value.startswith("http"):
            value = "http://" + value

        # if not a valid URL, just return empty string
        try:
            URLValidator(value)
        except ValidationError:
            return ""

        return value
