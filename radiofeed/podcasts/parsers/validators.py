import contextlib
import functools
from collections.abc import Iterable
from typing import Annotated, Any, Final, Literal, TypeVar

from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from pydantic import AfterValidator, BeforeValidator

from radiofeed.episodes.models import Episode
from radiofeed.podcasts.models import Podcast
from radiofeed.validators import url_validator

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


def pg_integer(value: Any) -> int | None:
    """Validate that value is within PostgreSQL integer range."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None

    if value not in _PG_INTEGER_RANGE:
        return None
    return value


def one_of(value: str | None, *, values: Iterable[str]) -> bool:
    """Validate that value is one of the given values (case insensitive)."""
    return bool(value and value.casefold() in values)


def default_if_none(value: Any, *, default: T) -> T:
    """Returns default if value is None."""
    return default if value is None else value


def one_of_choices(
    value: str | None,
    *,
    choices: type[TextChoices],
    default: str,
) -> str:
    """Validate that value is one of the given TextChoices."""
    if (value := (value or "").casefold()) in choices:
        return value
    return default


def url(value: str | None) -> str:
    """Validate and normalize a URL."""
    if value:
        if not value.startswith("http"):
            value = f"http://{value}"

        with contextlib.suppress(ValidationError):
            url_validator(value)
            return value
    return ""


OptionalUrl = Annotated[str | None, AfterValidator(url)]

PgInteger = Annotated[int | None, BeforeValidator(pg_integer)]

Explicit = Annotated[
    bool,
    BeforeValidator(
        functools.partial(one_of, values=("clean", "yes", "true")),
    ),
]

EmptyIfNone = Annotated[
    str, BeforeValidator(functools.partial(default_if_none, default=""))
]

EpisodeType = Annotated[
    str,
    BeforeValidator(
        functools.partial(
            one_of_choices,
            choices=Episode.EpisodeType,
            default=Episode.EpisodeType.FULL,
        )
    ),
]

PodcastType = Annotated[
    str,
    BeforeValidator(
        functools.partial(
            one_of_choices,
            choices=Podcast.PodcastType,
            default=Podcast.PodcastType.EPISODIC,
        )
    ),
]
