import contextlib
import datetime
import functools
import re
import unicodedata
from collections.abc import Iterator
from typing import Final

import pycountry
from django.conf import settings
from django.utils import timezone, translation
from django.utils.formats import date_format

from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tokenize import RegexpTokenizer
from radiofeed.html import strip_html

_STOPWORDS_LANGUAGES: Final = {
    "ar": "arabic",
    "az": "azerbaijani",
    "be": "belarusian",
    "bn": "bengali",
    "ca": "catalan",
    "da": "danish",
    "de": "german",
    "el": "greek",
    "en": "english",
    "es": "spanish",
    "eu": "basque",
    "fi": "finnish",
    "fr": "french",
    "he": "hebrew",
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
    "sq": "albanian",
    "sv": "swedish",
    "ta": "tamil",
    "tg": "tajik",
    "tr": "turkish",
    "zh": "chinese",
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
    return (
        _re_punctuation()
        .sub(
            "",
            _re_digits().sub(
                "",
                strip_html(text),
            ),
        )
        .strip()
    )


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
def get_language_codes() -> set[str]:
    """Return ISO 639 2-char language codes ."""
    return {
        language.alpha_2
        for language in pycountry.languages
        if hasattr(language, "alpha_2")
    }


@functools.cache
def get_stopwords(language: str) -> set[str]:
    """Return all stopwords for a language, if available.

    Args:
        language: 2-char language code e.g. "en"
    """

    return {
        _strip_accents(word).strip().casefold()
        for word in _CORPORATE_STOPWORDS
        | _get_corpus_stopwords(language)
        | _get_date_stopwords(language)
    }


def _lemmatized_tokens(text: str) -> Iterator[str]:
    for token in _tokenizer.tokenize(text):
        with contextlib.suppress(AttributeError):
            yield _lemmatizer.lemmatize(token)


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def _get_corpus_stopwords(language: str) -> set[str]:
    words = set()
    if name := _STOPWORDS_LANGUAGES.get(language):
        with contextlib.suppress(AttributeError):
            words.update(stopwords.words(name))

        path = settings.BASE_DIR / "nltk" / "stopwords" / f"{name}.txt"

        if path.exists():
            words.update(
                {
                    word
                    for word in (word.strip() for word in path.read_text().splitlines())
                    if word
                }
            )
    return words


def _get_date_stopwords(language: str) -> set[str]:
    now = timezone.now()
    words = set()
    with translation.override(language):
        for month in range(1, 13):
            dt = datetime.date(now.year, month, 1)
            words.add(date_format(dt, "b"))
            words.add(date_format(dt, "F"))

        for day in range(7):
            dt = now + timezone.timedelta(days=day)
            words.add(date_format(dt, "D"))
            words.add(date_format(dt, "l"))
    return words


@functools.cache
def _re_punctuation() -> re.Pattern:
    return re.compile(r"([^\s\w]|_:.?-)+", flags=re.UNICODE)


@functools.cache
def _re_digits() -> re.Pattern:
    return re.compile(r"\d+", flags=re.UNICODE)
