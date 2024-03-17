import contextlib
import functools
from datetime import datetime
from typing import Any, Final

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone

from radiofeed.feedparser.date_parser import parse_date

_PG_INTEGER_RANGE: Final = range(
    -2147483648,
    2147483647,
)

_AUDIO_MIMETYPES: Final = frozenset(
    [
        "audio/aac",
        "audio/aacp",
        "audio/basic",
        "audio/L24",
        "audio/m4a",
        "audio/midi",
        "audio/mp3",
        "audio/mp4",
        "audio/mp4a-latm",
        "audio/mp4a-latm",
        "audio/mpef",
        "audio/mpeg",
        "audio/mpeg3",
        "audio/mpeg4",
        "audio/mpg",
        "audio/ogg",
        "audio/video",
        "audio/vnd.dlna.adts",
        "audio/vnd.rn-realaudio",
        "audio/vnd.wave",
        "audio/vorbis",
        "audio/wav",
        "audio/wave",
        "audio/webm",
        "audio/x-aac",
        "audio/x-aiff",
        "audio/x-aiff",
        "audio/x-flac",
        "audio/x-hx-aac-adts",
        "audio/x-m4a",
        "audio/x-m4a",
        "audio/x-m4b",
        "audio/x-m4v",
        "audio/x-mov",
        "audio/x-mp3",
        "audio/x-mpeg",
        "audio/x-mpg",
        "audio/x-ms-wma",
        "audio/x-pn-realaudio",
        "audio/x-wav",
    ]
)


_url_validator = URLValidator(["http", "https"])


def pg_integer(value: Any) -> int | None:
    """Check is an integer, and ensure within Postgres integer range values."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None

    if value not in _PG_INTEGER_RANGE:
        return None
    return value


def language(value: str) -> str:
    """Returns two-character language code."""
    return value[:2].casefold()


def url(value: str | None, *, required: bool = False) -> str | None:
    """Returns a URL value. Will try to prefix with https:// if only domain provided.

    If cannot resolve as a valid URL will return None.
    """
    if value:
        if not value.startswith("http"):
            value = f"http://{value}"

        with contextlib.suppress(ValidationError):
            _url_validator(value)
            return value
    if required:
        raise ValueError("url is required")
    return None


def duration(value: str | None) -> str:
    """Given a duration value will ensure all values fall within range.

    Examples:
        - 3600 (plain int) -> "3600"
        - 3:60:50:1000 -> "3:60:50"

    Return empty string if cannot resolve.

    Args:
        value (str | None)

    Returns:
        str
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
            [str(v) for v in [int(v) for v in value.split(":")[:3]] if v in range(60)]
        )

    except ValueError:
        return ""


def one_of(value: str | None, *, values: tuple[str]) -> bool:
    """Checks if value in list."""
    return bool(value and value.casefold() in values)


explicit = functools.partial(one_of, values=("yes", "clean"))

complete = functools.partial(one_of, values=("yes"))


def audio_mimetype(value: Any) -> str:
    """Checks if an audio mime type"""
    if value in _AUDIO_MIMETYPES:
        return value
    raise ValueError(f"{value} is not an audio mime type")


def pub_date(value: Any) -> datetime:
    """Checks is valid datetime value and not in the future."""
    value = parse_date(value)
    if value is None:
        raise ValueError("pub_date cannot be none")
    if value > timezone.now():
        raise ValueError("pub_date cannot be in future")
    return value
