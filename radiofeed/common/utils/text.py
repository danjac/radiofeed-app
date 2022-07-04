import datetime
import html
import pathlib
import re

from datetime import timedelta
from functools import lru_cache

from django.template.defaultfilters import striptags
from django.utils import timezone, translation
from django.utils.formats import date_format
from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tokenize import RegexpTokenizer

NLTK_LANGUAGES = {
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

_corporate_stopwords = [
    "apple",
    "patreon",
    "spotify",
    "stitcher",
    "itunes",
]

_tokenizer = RegexpTokenizer(r"\w+")
_lemmatizer = WordNetLemmatizer()

_stopwords_dir = pathlib.Path(__file__).resolve(strict=True).parent / "stopwords"


@lru_cache()
def get_stopwords(language):
    """Return all stopwords for a language, if available.

    Args:
        language (str): 2-char language code e.g. "en"

    Returns:
        frozenset[str]
    """
    try:
        return frozenset(
            stopwords.words(NLTK_LANGUAGES[language])
            + _corporate_stopwords
            + _get_extra_stopwords(language)
            + list(_get_date_stopwords(language))
        )

    except (AttributeError, KeyError, OSError):
        return frozenset()


def clean_text(text):
    """Scrub text of any HTML tags and entities, punctuation and numbers.

    Args:
        text (str): text to be cleaned

    Returns:
        str: cleaned text
    """
    text = html.unescape(striptags(text.strip()))
    text = re.sub(r"([^\s\w]|_:.?-)+", "", text)
    text = re.sub(r"\d+", "", text)
    return text


def tokenize(language, text):
    """Extract all relevant keywords from text, removing any stopwords, HTML tags etc.

    Args:
        language (str): 2-char language code e.g. "en"
        text(str): text source

    Returns:
        list[str]
    """
    if not (text := clean_text(text).casefold()):
        return []

    stopwords_for_language = get_stopwords(language)

    return [
        token
        for token in _lemmatized_tokens(text)
        if token and token not in stopwords_for_language
    ]


def _get_date_stopwords(language):
    now = timezone.now()
    with translation.override(language):

        for month in range(1, 13):
            dt = datetime.date(now.year, month, 1)
            yield _format_date(dt, "b")
            yield _format_date(dt, "F")

        for day in range(0, 7):
            dt = now + timedelta(days=day)
            yield _format_date(dt, "D")
            yield _format_date(dt, "l")


def _get_extra_stopwords(language):
    path = _stopwords_dir / f"stopwords_{language}.txt"

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


def _lemmatized_tokens(text):
    for token in _tokenizer.tokenize(text):
        try:
            yield _lemmatizer.lemmatize(token)

        except AttributeError:
            # threading issue:
            # 'WordNetCorpusReader' object has no attribute '_LazyCorpusLoader__args'
            continue


def _format_date(value, fmt):
    return date_format(value, fmt).casefold()
