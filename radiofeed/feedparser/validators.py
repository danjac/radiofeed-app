import attrs

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

_audio_mimetypes = (
    "audio/aac",
    "audio/aacp",
    "audio/basic",
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
    "audio/vnd.wave",
    "audio/wav",
    "audio/wave",
    "audio/x-aac",
    "audio/x-aiff",
    "audio/x-aiff",
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
)

# ensure integer falls within PostgreSQL INTEGER range

pg_integer = attrs.validators.and_(
    attrs.validators.gt(-2147483648),
    attrs.validators.lt(2147483647),
)

audio = attrs.validators.in_(_audio_mimetypes)

_url_validator = URLValidator(["http", "https"])


def required(instance, attr, value):
    """Checks if value is truthy.

    Args:
        instance (object | None)
        attr (attrs.Attribute)
        value (Any)

    Raises:
        ValueError: any falsy value
    """
    if not value:
        raise ValueError(f"{attr=} cannot be empty or None")


def url(instance, attr, value):
    """Checks if value is a valid URL.

    Args:
        instance (object | None)
        attr (attrs.Attribute)
        value (Any)

    Raises:
        ValueError: invalid URL
    """
    try:
        _url_validator(value)
    except ValidationError as e:
        raise ValueError from e
