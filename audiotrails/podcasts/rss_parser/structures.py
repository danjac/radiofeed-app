from __future__ import annotations

import dataclasses

from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, RegexValidator, URLValidator
from django.utils import timezone

from audiotrails.podcasts.rss_parser.date_parser import parse_date


@dataclasses.dataclass
class Headers:
    etag: str = ""
    last_modified: datetime | None = None
    date: datetime | None = None


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
    except ValidationError:
        return ""

    return url


# validators

_validate_audio_type_length = MaxLengthValidator(60)
_validate_audio_type = RegexValidator(r"^audio/*")
_validate_duration_length = MaxLengthValidator(30)
_validate_url_length = MaxLengthValidator(500)
_validate_url = URLValidator(schemes=["http", "https"])
