import contextlib

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

_url_validator = URLValidator(["http", "https"])


def language(value: str) -> str:
    """Returns two-character language code."""
    return value[:2].casefold()


def explicit(value: str | None) -> bool:
    """Checks if podcast or episode explicit."""
    return bool(value and value.casefold() in ("clean", "yes"))


def url(value: str | None) -> str | None:
    """Returns a URL value. Will try to prefix with https:// if only domain provided.

    If cannot resolve as a valid URL will return None.

    Args:
        value (str | None)

    Returns:
        str | None
    """
    if value:
        if not value.startswith("http"):
            value = f"http://{value}"

        with contextlib.suppress(ValidationError):
            _url_validator(value)
            return value
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
