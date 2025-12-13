import contextlib
import functools
from collections.abc import Iterable
from datetime import datetime
from typing import Annotated, Any, ClassVar, Final, Literal, TypeVar

from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.utils import timezone
from django.utils.text import slugify
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    field_validator,
    model_validator,
)

from listenwave import tokenizer
from listenwave.episodes.models import Episode
from listenwave.feed_parser.date_parser import parse_date
from listenwave.podcasts.models import Podcast
from listenwave.validators import url_validator

AudioMimetype = Literal[
    "audio/aac",
    "audio/aacp",
    "audio/basic",
    "audio/L24",  # Assuming PCM 24-bit WAV-like format
    "audio/m4a",
    "audio/midi",
    "audio/mp3",
    "audio/mp4",
    "audio/mp4a-latm",
    "audio/mpef",
    "audio/mpeg",
    "audio/mpeg3",
    "audio/mpeg4",
    "audio/mpg",
    "audio/ogg",
    "audio/video",  # Not a common audio type, assuming default
    "audio/vnd.dlna.adts",
    "audio/vnd.rn-realaudio",  # RealAudio varies, assuming standard quality
    "audio/vnd.wave",
    "audio/vorbis",
    "audio/wav",
    "audio/wave",
    "audio/webm",
    "audio/x-aac",
    "audio/x-aiff",
    "audio/x-flac",
    "audio/x-hx-aac-adts",
    "audio/x-m4a",
    "audio/x-m4b",
    "audio/x-m4v",  # Assuming similar to M4A
    "audio/x-mov",  # Assuming similar to M4A
    "audio/x-mp3",
    "audio/x-mpeg",
    "audio/x-mpg",
    "audio/x-ms-wma",
    "audio/x-pn-realaudio",
    "audio/x-wav",
]

T = TypeVar("T")


_PG_INTEGER_RANGE: Final = range(
    -2147483648,
    2147483647,
)


def _pg_integer(value: Any) -> int | None:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None

    if value not in _PG_INTEGER_RANGE:
        return None
    return value


def _one_of(value: str | None, *, values: Iterable[str]) -> bool:
    return bool(value and value.casefold() in values)


def _default_if_none(value: Any, *, default: T) -> T:
    return default if value is None else value


def _one_of_choices(
    value: str | None,
    *,
    choices: type[TextChoices],
    default: str,
) -> str:
    if (value := (value or "").casefold()) in choices:
        return value
    return default


def _url(value: str | None) -> str:
    if value:
        if not value.startswith("http"):
            value = f"http://{value}"

        with contextlib.suppress(ValidationError):
            url_validator(value)
            return value
    return ""


OptionalUrl = Annotated[str | None, AfterValidator(_url)]

PgInteger = Annotated[int | None, BeforeValidator(_pg_integer)]

Explicit = Annotated[
    bool,
    BeforeValidator(
        functools.partial(_one_of, values=("clean", "yes", "true")),
    ),
]

EmptyIfNone = Annotated[
    str, BeforeValidator(functools.partial(_default_if_none, default=""))
]

EpisodeType = Annotated[
    str,
    BeforeValidator(
        functools.partial(
            _one_of_choices,
            choices=Episode.EpisodeType,
            default=Episode.EpisodeType.FULL,
        )
    ),
]

PodcastType = Annotated[
    str,
    BeforeValidator(
        functools.partial(
            _one_of_choices,
            choices=Podcast.PodcastType,
            default=Podcast.PodcastType.EPISODIC,
        )
    ),
]


class Item(BaseModel):
    """Individual item or episode in RSS or Atom podcast feed."""

    guid: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)

    description: EmptyIfNone = ""
    keywords: EmptyIfNone = ""

    pub_date: datetime

    media_url: str
    media_type: AudioMimetype

    cover_url: OptionalUrl = ""
    website: OptionalUrl = ""

    explicit: Explicit = False

    file_size: PgInteger = None

    duration: str = ""

    season: PgInteger = None
    episode: PgInteger = None

    episode_type: EpisodeType = Episode.EpisodeType.FULL

    @field_validator("pub_date", mode="before")
    @classmethod
    def validate_pub_date(cls, value: Any) -> datetime:
        """Checks is valid datetime value and not in the future."""
        value = parse_date(value)
        if value is None:
            raise ValueError("pub_date cannot be none")
        if value > timezone.now():
            raise ValueError("pub_date cannot be in future")
        return value

    @field_validator("media_url", mode="after")
    @classmethod
    def validate_media_url(cls, value: Any) -> str:
        """Validate media url"""
        if not _url(value):
            raise ValueError("url is required")
        return value

    @field_validator("duration", mode="before")
    @classmethod
    def validate_duration(cls, value: Any) -> str:
        """Given a duration value will ensure all values fall within range.

        Examples:
            - 3600 (plain int) -> "3600"
            - 3:60:50:1000 -> "3:60:50"

        Return empty string if cannot resolve.
        """
        if not value:
            return ""

        try:
            # plain seconds value
            return str(int(value))
        except ValueError:
            pass

        try:
            return ":".join(
                [
                    str(v)
                    for v in [int(v) for v in value.split(":")[:3]]
                    if v in range(60)
                ]
            )

        except ValueError:
            return ""


class Feed(BaseModel):
    """RSS/Atom Feed model."""

    DEFAULT_LANGUAGE: ClassVar[str] = "en"

    title: str = Field(..., min_length=1)

    owner: EmptyIfNone = ""
    description: EmptyIfNone = ""

    language: str = DEFAULT_LANGUAGE
    pub_date: datetime | None = None

    canonical_url: OptionalUrl = ""
    website: OptionalUrl = ""
    cover_url: OptionalUrl = ""

    funding_text: EmptyIfNone = ""
    funding_url: OptionalUrl = ""

    keywords: EmptyIfNone = ""

    explicit: Explicit = False
    complete: bool = False

    podcast_type: PodcastType = Podcast.PodcastType.EPISODIC

    categories: set[str] = Field(default_factory=set)

    items: list[Item]

    @field_validator("language", mode="before")
    @classmethod
    def validate_language(cls, value: Any) -> str:
        """Validate media type."""
        if value and len(value) > 1:
            value = value.casefold()[:2]
            if value in tokenizer.get_language_codes():
                return value
        return cls.DEFAULT_LANGUAGE

    @field_validator("complete", mode="before")
    @classmethod
    def validate_complete(cls, value: Any) -> bool:
        """Validate complete."""
        return _one_of(value, values=("yes", "true"))

    @field_validator("categories", mode="before")
    @classmethod
    def validate_categories(cls, value: Any) -> set[str]:
        """Ensure categories are sorted.

        1. Normalize categories by stripping whitespace and casefolding.
        2. Replace "&amp;/and" and with " & "
        3. Split categories on common separators and add to set.
        4. Slugify categories to ensure consistent format.
        """
        categories = set()
        for category in value:
            if (
                normalized := category.strip()
                .casefold()
                .replace(" &amp; ", " & ")
                .replace(" and ", " & ")
            ):
                categories.add(normalized)
                for sep in (" ", "/", "&", ",", "+"):
                    categories.update(normalized.split(sep))
        # Slugify keywords to ensure consistent format
        return {c for c in (slugify(c, allow_unicode=False) for c in categories) if c}

    @model_validator(mode="after")
    def validate_pub_date(self) -> "Feed":
        """Set default pub date based on max items pub date."""
        self.pub_date = max(self.pub_dates)
        return self

    @property
    def pub_dates(self) -> list[datetime]:
        """Return sorted list of pub dates for all items in feed."""
        return [item.pub_date for item in self.items]

    def tokenize(self) -> str:
        """Tokenize feed for search."""
        text = " ".join(
            [
                value
                for value in [
                    self.title,
                    self.description,
                    self.owner,
                    *self.categories,
                    *self.keywords.split(","),
                    *[item.title for item in self.items][:6],
                ]
                if value
            ]
        )
        return " ".join(tokenizer.tokenize(self.language, text))
