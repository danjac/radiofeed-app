import datetime
import re
from collections.abc import Iterator
from datetime import date, timedelta
from functools import lru_cache
from typing import Final

from django.conf import settings
from django.utils import timezone, translation
from django.utils.formats import date_format

from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tokenize import RegexpTokenizer
from radiofeed import cleaners

NLTK_LANGUAGES: Final = {
    "ar": "arabic",
    "az": "azerbaijani",
    "da": "danish",
    "de": "german",
    "el": "greek",
    "en": "english",
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
}

_CORPORATE_STOPWORDS: Final = [
    "apple",
    "patreon",
    "spotify",
    "stitcher",
    "itunes",
]


_tokenizer = RegexpTokenizer(r"\w+")
_lemmatizer = WordNetLemmatizer()


@lru_cache
def get_stopwords(language: str) -> frozenset[str]:
    """Return all stopwords for a language, if available.

    Args:
        language: 2-char language code e.g. "en"
    """
    try:
        return frozenset(
            stopwords.words(NLTK_LANGUAGES[language])
            + _CORPORATE_STOPWORDS
            + _get_extra_stopwords(language)
            + list(_get_date_stopwords(language))
        )

    except (AttributeError, KeyError, OSError):
        return frozenset()


def clean_text(text: str) -> str:
    """Scrub text of any HTML tags and entities, punctuation and numbers."""
    text = cleaners.strip_html(text)
    text = re.sub(r"([^\s\w]|_:.?-)+", "", text)
    return re.sub(r"\d+", "", text)


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


def _get_date_stopwords(language: str) -> Iterator[str]:
    now = timezone.now()
    with translation.override(language):
        for month in range(1, 13):
            dt = datetime.date(now.year, month, 1)
            yield _format_date(dt, "b")
            yield _format_date(dt, "F")

        for day in range(7):
            dt = now + timedelta(days=day)
            yield _format_date(dt, "D")
            yield _format_date(dt, "l")


def _get_extra_stopwords(language: str) -> list[str]:
    path = settings.BASE_DIR / "nltk" / "stopwords" / f"stopwords_{language}.txt"

    return (
        [
            word
            for word in (
                word.strip().casefold() for word in path.read_text().splitlines()
            )
            if word
        ]
        if path.exists()
        else []
    )


def _lemmatized_tokens(text: str) -> Iterator[str]:
    for token in _tokenizer.tokenize(text):
        try:
            yield _lemmatizer.lemmatize(token)

        except AttributeError:
            # threading issue:
            # 'WordNetCorpusReader' object has no attribute '_LazyCorpusLoader__args'
            continue


def _format_date(value: date, fmt: str) -> str:
    return date_format(value, fmt).casefold()
