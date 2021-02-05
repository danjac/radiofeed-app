import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, conlist, constr, validator


class Audio(BaseModel):
    type: constr(max_length=60)  # type: ignore
    url: HttpUrl
    length: int = 0

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


class Feed(BaseModel):
    title: str
    description: str
    explicit: bool = False
    language: str = "en"
    items: conlist(Item, min_items=1)  # type: ignore
    authors: List[str]
    image: Optional[str]
    link: Optional[HttpUrl]
    categories: List[str]

    @validator("link", pre=True)
    def add_http_to_domain(cls, value: Optional[str]) -> Optional[str]:
        # links often just consist of domain
        if not value:
            return value
        if not value.startswith("http"):
            value = "http://" + value
        return value
