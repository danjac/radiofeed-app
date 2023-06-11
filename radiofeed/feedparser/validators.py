from typing import Any, Final

import attrs
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

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

# ensure integer falls within PostgreSQL INTEGER range

pg_integer = attrs.validators.and_(
    attrs.validators.gt(-2147483648),
    attrs.validators.lt(2147483647),
)

audio = attrs.validators.in_(_AUDIO_MIMETYPES)

_url_validator = URLValidator(["http", "https"])


def required(instance: Any, attr: attrs.Attribute, value: Any) -> None:
    """Checks if value is truthy.

    Raises:
        ValueError: any falsy value
    """
    if not value:
        msg = f"{attr=} cannot be empty or None"
        raise ValueError(msg)


def url(instance: Any, attr: attrs.Attribute, value: Any) -> None:
    """Checks if value is a valid URL.

    Raises:
        ValueError: invalid URL
    """
    try:
        _url_validator(value)
    except ValidationError as e:
        msg = f"{attr=} must be a URL"
        raise ValueError(msg) from e
