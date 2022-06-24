from __future__ import annotations

from datetime import datetime
from typing import Callable, TypeVar

import attrs

from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, URLValidator
from django.utils import timezone

from radiofeed.podcasts.parsers import date_parser

_url_validator = URLValidator(["http", "https"])

T = TypeVar("T")


AUDIO_MIMETYPES = (
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


LANGUAGE_CODES = (
    "aa",
    "ab",
    "ae",
    "af",
    "ak",
    "am",
    "an",
    "ar",
    "as",
    "av",
    "ay",
    "az",
    "ba",
    "be",
    "bg",
    "cv",
    "cy",
    "da",
    "de",
    "dv",
    "dz",
    "ee",
    "el",
    "en",
    "eo",
    "es",
    "et",
    "eu",
    "fa",
    "ff",
    "fi",
    "fj",
    "fo",
    "fr",
    "fy",
    "ga",
    "gd",
    "gl",
    "gn",
    "gu",
    "gv",
    "ha",
    "he",
    "hi",
    "ho",
    "hr",
    "ht",
    "hu",
    "hy",
    "hz",
    "ia",
    "id",
    "ie",
    "ig",
    "ii",
    "ik",
    "io",
    "is",
    "it",
    "iu",
    "ja",
    "jv",
    "ka",
    "kg",
    "ki",
    "kj",
    "kk",
    "kl",
    "km",
    "kn",
    "ko",
    "kr",
    "ks",
    "ku",
    "kv",
    "kw",
    "ky",
    "la",
    "lb",
    "lg",
    "li",
    "ln",
    "lo",
    "lt",
    "lu",
    "lv",
    "mg",
    "mh",
    "mi",
    "mk",
    "ml",
    "mn",
    "mr",
    "ms",
    "mt",
    "my",
    "na",
    "nb",
    "nd",
    "nv",
    "ny",
    "oc",
    "oj",
    "om",
    "or",
    "os",
    "pa",
    "pi",
    "pl",
    "ps",
    "pt",
    "qu",
    "rm",
    "rn",
    "ro",
    "ru",
    "rw",
    "sa",
    "sc",
    "sd",
    "se",
    "sg",
    "si",
    "sk",
    "sl",
    "sm",
    "sn",
    "so",
    "sq",
    "sr",
    "ss",
    "st",
    "su",
    "sv",
    "sw",
    "ta",
    "te",
    "tg",
    "th",
    "ti",
    "tk",
    "tl",
    "tn",
    "to",
    "tr",
    "ts",
    "tt",
    "tw",
    "ty",
    "ug",
    "uk",
    "ur",
    "uz",
    "ve",
    "vi",
    "vo",
    "wa",
    "wo",
    "xh",
    "yi",
    "yo",
    "za",
    "zh",
    "zu",
)


def int_in_range(inst: T, attr: attrs.Attribute, value: int | None) -> None:
    if value and value not in range(-2147483648, 2147483647):
        raise ValueError(f"{value=} out of range")


def pub_date(inst: T, attr: attrs.Attribute, value: datetime) -> None:
    if value > timezone.now():
        raise ValueError("pub_date cannot be in future")


def min_len(length: int) -> Callable:
    def _validate(inst: T, attr: attrs.Attribute, value: str | None) -> None:
        try:
            MinLengthValidator(length)(value or "")
        except ValidationError as e:
            raise ValueError from e

    return _validate


def url(inst: T, attr: attrs.Attribute, value: str | None) -> None:
    if value:
        try:
            _url_validator(value)
        except ValidationError as e:
            raise ValueError from e


def is_complete(value: str) -> bool:
    return bool(value and value.casefold() == "yes")


def is_explicit(value: str) -> bool:
    return bool(value and value.casefold() in ("clean", "yes"))


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


def language_code(value: str) -> str:
    return (value or "en")[:2]


def int_or_none(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@attrs.define(kw_only=True)
class Outline:

    title: str = ""
    text: str = ""

    rss: str | None = attrs.field(validator=url, default=None)
    url: str | None = attrs.field(validator=url, default=None)


@attrs.define(kw_only=True)
class Item:

    guid: str = attrs.field(validator=min_len(1))
    title: str = attrs.field(validator=min_len(1))

    pub_date: datetime = attrs.field(
        converter=date_parser.parse_date,
        validator=[attrs.validators.instance_of(datetime), pub_date],
    )

    media_url: str = attrs.field(validator=url)
    media_type: str = attrs.field(validator=attrs.validators.in_(AUDIO_MIMETYPES))

    link: str | None = attrs.field(validator=url, default=None)

    explicit: bool = attrs.field(converter=is_explicit, default=False)

    length: int | None = attrs.field(
        converter=int_or_none, default=None, validator=int_in_range
    )
    season: int | None = attrs.field(
        converter=int_or_none, default=None, validator=int_in_range
    )
    episode: int | None = attrs.field(
        converter=int_or_none, default=None, validator=int_in_range
    )

    cover_url: str | None = attrs.field(validator=url, default=None)

    duration: str = attrs.field(converter=duration, default="")

    episode_type: str = "full"
    description: str = ""
    keywords: str = ""


@attrs.define(kw_only=True)
class Feed:

    title: str = attrs.field(validator=min_len(1))

    language: str = attrs.field(
        converter=language_code,
        validator=attrs.validators.in_(LANGUAGE_CODES),
    )

    link: str | None = attrs.field(validator=url, default=None)
    cover_url: str | None = attrs.field(validator=url, default=None)

    complete: bool = attrs.field(converter=is_complete, default=False)

    explicit: bool = attrs.field(converter=is_explicit, default=False)

    owner: str = ""
    description: str = ""

    funding_text: str = ""
    funding_url: str | None = attrs.field(validator=url, default=None)

    categories: list[str] = attrs.field(default=attrs.Factory(list))

    items: list[Item] = attrs.field(
        default=attrs.Factory(list),
        validator=min_len(1),
    )

    @property
    def latest_pub_date(self) -> datetime:
        return max([item.pub_date for item in self.items])
