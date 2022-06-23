from __future__ import annotations

from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone

from radiofeed.podcasts.parsers import date_parser

_validate_url = URLValidator(["http", "https"])

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


def text(*values: str, required: bool = False, default: str = "") -> str:

    try:
        return next(iter(values))
    except StopIteration:
        if required:
            raise ValueError
        return default


def audio(*values: str) -> str:
    for value in values:
        if (rv := value.casefold()) in AUDIO_MIMETYPES:
            return rv

    raise ValueError


def pub_date(*values: str) -> datetime:
    for value in values:
        if (pub_date := date_parser.parse_date(value)) and pub_date > timezone.now():
            return pub_date
    raise ValueError


def explicit(*values: str) -> bool:
    for value in values:
        if value.casefold() in ("clean", "yes"):
            return True
    return False


def boolean(*values: str, default: bool = False) -> bool:
    for value in values:
        if value.casefold() == "yes":
            return True
    return default


def language(*values: str, default: str = "en") -> str:
    for value in values:
        if (language := value[:2].casefold()) in LANGUAGE_CODES:
            return language

    return default


def url(*values: str, required: bool = False) -> str | None:

    for value in values:
        try:
            _validate_url(value)
            return value
        except ValidationError:
            continue
    if required:
        raise ValueError
    return None


def integer(*values: str, required: bool = False) -> int | None:

    for value in values:
        try:
            if (result := int(value)) in range(-2147483648, 2147483647):
                return result
        except ValueError:
            continue
    if required:
        raise ValueError
    return None


def duration(*values: str) -> str:
    for value in values:
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
            continue
    return ""
