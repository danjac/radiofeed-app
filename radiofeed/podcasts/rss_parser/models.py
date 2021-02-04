import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, conlist


class Audio(BaseModel):
    type: str
    url: HttpUrl
    length: Optional[int]


class Item(BaseModel):
    audio: Audio
    title: str
    guid: str
    explicit: bool
    description: str
    pub_date: datetime.datetime
    duration: str
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
