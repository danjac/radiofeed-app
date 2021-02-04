import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, conlist, constr, validator


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
    explicit: bool
    description: str
    pub_date: datetime.datetime
    duration: constr(max_length=30)  # type: ignore
    keywords: str


class Feed(BaseModel):
    title: str
    description: str
    explicit: bool
    authors: List[str]
    link: Optional[HttpUrl]
    language: Optional[str]
    image: Optional[str]
    categories: List[str]
    items: conlist(Item, min_items=1)  # type: ignore
