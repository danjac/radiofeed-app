from __future__ import annotations

from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone

from radiofeed.podcasts.parsers import date_parser

_validate_url = URLValidator(["http", "https"])


def audio(value: str) -> str:
    if not value.startswith("audio/"):
        raise ValueError("not a valid audio enclosure")
    return value


def pub_date(value: str) -> datetime:
    if not (pub_date := date_parser.parse_date(value)) or pub_date > timezone.now():
        raise ValueError("not a valid pub date")
    return pub_date


def explicit(value: str) -> bool:
    return value.casefold() in ("clean", "yes")


def url(value: str, raises: bool = False) -> str | None:
    try:
        _validate_url(value)
        return value
    except ValidationError as e:
        if raises:
            raise ValueError from e
    return None


def integer(value: str) -> int | None:

    try:
        if (result := int(value)) in range(-2147483648, 2147483647):
            return result
    except ValueError:
        pass
    return None


def duration(value: str) -> str:
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
                if v in range(0, 60)
            ]
        )
    except ValueError:
        return ""
