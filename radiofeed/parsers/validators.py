import contextlib
from typing import TYPE_CHECKING, Any, Final, TypeVar

from django.core.exceptions import ValidationError

from radiofeed.db.validators import url_validator

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db.models import TextChoices

T = TypeVar("T")


_PG_INTEGER_RANGE: Final = range(
    -2147483648,
    2147483647,
)


def pg_integer(value: Any) -> int | None:
    """Validate that value is within PostgreSQL integer range."""
    try:
        value = int(value)
    except TypeError, ValueError:
        return None

    if value not in _PG_INTEGER_RANGE:
        return None
    return value


def is_one_of(value: str | None, *, values: Iterable[str]) -> bool:
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


def normalize_url(value: str | None) -> str:
    """Validate and normalize a URL.
    If the URL does not start with 'http' or 'https', 'http://' is prepended.
    If the URL is invalid, an empty string is returned.
    """
    if value:
        if not value.startswith("http"):
            value = f"http://{value}"

        with contextlib.suppress(ValidationError):
            url_validator(value)
            return value
    return ""
