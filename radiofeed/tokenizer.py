import contextlib
import datetime
import functools
import pathlib
import re
import unicodedata
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Final

from django.conf import settings
from django.utils import timezone, translation
from django.utils.formats import date_format

from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tokenize import RegexpTokenizer
from radiofeed.html import strip_html

LANGUAGE_CODES: Final = {
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
    "bi",
    "bm",
    "bn",
    "bo",
    "br",
    "bs",
    "ca",
    "ce",
    "ch",
    "co",
    "cr",
    "cs",
    "cu",
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
    "ne",
    "ng",
    "nl",
    "nn",
    "no",
    "nr",
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
    "sh",
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
}

_STOPWORDS_LANGUAGES: Final = {
    "ar": "arabic",
    "az": "azerbaijani",
    "da": "danish",
    "de": "german",
    "el": "greek",
    "en": "english",
    "eo": "esperanto",
    "es": "spanish",
    "fi": "finnish",
    "fr": "french",
    "hu": "hungarian",
    "id": "indonesian",
    "it": "italian",
    "kk": "kazakh",
    "ne": "nepali",
    "nl": "dutch",
    "no": "norwegian",
    "pt": "portuguese",
    "ro": "romanian",
    "ru": "russian",
    "sl": "slovene",
    "sv": "swedish",
    "tg": "tajik",
    "tr": "turkish",
    "uk": "ukrainian",
}

_CORPORATE_STOPWORDS: Final = {
    "apple",
    "patreon",
    "spotify",
    "stitcher",
    "itunes",
}

_lemmatizer = WordNetLemmatizer()
_tokenizer = RegexpTokenizer(r"\w+")


def clean_text(text: str) -> str:
    """Scrub text of any HTML tags and entities, punctuation and numbers."""
    return _remove_digits_and_punctuation(strip_html(text)).strip()


def tokenize(language: str, text: str) -> list[str]:
    """Extract all relevant keywords from text, removing any stopwords, HTML tags etc.

    Args:
        language: 2-char language code e.g. "en"
        text: text source
    """
    if text := clean_text(text).casefold():
        stopwords_for_language = get_stopwords(language)

        return [
            token
            for token in _lemmatized_tokens(text)
            if token and token not in stopwords_for_language
        ]
    return []


@functools.cache
def get_stopwords(language: str) -> set[str]:
    """Return all stopwords for a language, if available.

    Args:
        language: 2-char language code e.g. "en"
    """

    stopwords = {
        _strip_accents(word).casefold()
        for word in _CORPORATE_STOPWORDS
        | _get_corpus_stopwords(language)
        | _get_date_stopwords(language)
        | _get_extra_stopwords(language)
    }

    # Compatibility with hash-based stopword lists
    stopwords.update(_re_token().findall(" ".join(stopwords)))

    return stopwords


def _lemmatized_tokens(text: str) -> Iterator[str]:
    for token in _tokenizer.tokenize(text):
        with contextlib.suppress(AttributeError):
            yield _lemmatizer.lemmatize(token)


def _format_date(value: date, fmt: str) -> str:
    return date_format(value, fmt).casefold()


def _remove_digits_and_punctuation(text: str) -> str:
    """Strip non-alphanumeric characters from text."""
    return _re_punctuation().sub("", _re_digits().sub("", text))


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


@functools.cache
def _get_date_stopwords(language: str) -> set[str]:
    now = timezone.now()
    stopwords = set()
    with translation.override(language):
        for month in range(1, 13):
            dt = datetime.date(now.year, month, 1)
            stopwords.add(_format_date(dt, "b"))
            stopwords.add(_format_date(dt, "F"))

        for day in range(7):
            dt = now + timedelta(days=day)
            stopwords.add(_format_date(dt, "D"))
            stopwords.add(_format_date(dt, "l"))
    return stopwords


@functools.cache
def _get_extra_stopwords(language: str) -> set[str]:
    if (path := _extra_stopwords_path(language)) and path.exists():
        return {
            word
            for word in (
                word.strip().casefold() for word in path.read_text().splitlines()
            )
            if word
        }
    return set()


@functools.cache
def _get_corpus_stopwords(language: str) -> set[str]:
    if name := _get_stopwords_language(language):
        with contextlib.suppress(AttributeError, KeyError, OSError):
            return set(stopwords.words(name))
    return set()


@functools.cache
def _get_stopwords_language(language: str) -> str | None:
    return _STOPWORDS_LANGUAGES.get(language, None)


@functools.cache
def _extra_stopwords_path(language: str) -> pathlib.Path | None:
    if name := _get_stopwords_language(language):
        return settings.BASE_DIR / "nltk" / "stopwords" / f"{name}.txt"
    return None


@functools.cache
def _re_token() -> re.Pattern:
    return re.compile(r"\b\w+\b", flags=re.UNICODE)


@functools.cache
def _re_punctuation() -> re.Pattern:
    return re.compile(r"([^\s\w]|_:.?-)+", flags=re.UNICODE)


@functools.cache
def _re_digits() -> re.Pattern:
    return re.compile(r"\d+", flags=re.UNICODE)
