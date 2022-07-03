import datetime
import html
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

_corporates = [
    "apple",
    "patreon",
    "spotify",
    "stitcher",
    "itunes",
]

_stopwords = {
    "en": [
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "across",
        "advice",
        "along",
        "also",
        "always",
        "answer",
        "around",
        "audio",
        "available",
        "back",
        "become",
        "behind",
        "best",
        "better",
        "beyond",
        "big",
        "biggest",
        "bring",
        "brings",
        "change",
        "channel",
        "city",
        "come",
        "content",
        "conversation",
        "course",
        "daily",
        "date",
        "day",
        "days",
        "different",
        "discussion",
        "dont",
        "dr",
        "end",
        "enjoy",
        "episode",
        "episodes",
        "even",
        "ever",
        "every",
        "everyone",
        "everything",
        "favorite",
        "feature",
        "featuring",
        "feed",
        "field",
        "find",
        "first",
        "focus",
        "follow",
        "full",
        "fun",
        "get",
        "give",
        "go",
        "going",
        "good",
        "gmt",
        "great",
        "guest",
        "happen",
        "happening",
        "hear",
        "host",
        "hosted",
        "hour",
        "idea",
        "impact",
        "important",
        "including",
        "information",
        "inside",
        "insight",
        "interesting",
        "interview",
        "issue",
        "join",
        "journalist",
        "keep",
        "know",
        "knowledge",
        "known",
        "latest",
        "leading",
        "learn",
        "let",
        "life",
        "like",
        "listen",
        "listener",
        "little",
        "live",
        "look",
        "looking",
        "made",
        "make",
        "making",
        "many",
        "matter",
        "medium",
        "member",
        "minute",
        "moment",
        "month",
        "mr",
        "mrs",
        "ms",
        "much",
        "name",
        "need",
        "never",
        "new",
        "news",
        "next",
        "night",
        "offer",
        "open",
        "original",
        "other",
        "others",
        "part",
        "past",
        "people",
        "personal",
        "perspective",
        "place",
        "podcast",
        "podcasts",
        "premium",
        "present",
        "problem",
        "produced",
        "producer",
        "product",
        "production",
        "question",
        "radio",
        "read",
        "real",
        "really",
        "review",
        "right",
        "scene",
        "season",
        "see",
        "series",
        "set",
        "share",
        "short",
        "show",
        "shows",
        "side",
        "sign",
        "sir",
        "small",
        "something",
        "sometimes",
        "sound",
        "special",
        "sponsor",
        "start",
        "stories",
        "story",
        "subscribe",
        "support",
        "take",
        "tale",
        "talk",
        "talking",
        "team",
        "tell",
        "thing",
        "think",
        "thought",
        "time",
        "tip",
        "today",
        "together",
        "top",
        "topic",
        "training",
        "true",
        "truth",
        "understand",
        "unique",
        "use",
        "ustream",
        "video",
        "visit",
        "voice",
        "want",
        "way",
        "week",
        "weekly",
        "welcome",
        "well",
        "were",
        "what",
        "word",
        "work",
        "world",
        "would",
        "year",
        "years",
        "youll",
        "youre",
    ]
}

_tokenizer = RegexpTokenizer(r"\w+")
_lemmatizer = WordNetLemmatizer()


@lru_cache()
def get_stopwords(language):
    """Returns all stopwords for a language, if available.

    Args:
        language (str): 2-char language code e.g. "en"

    Returns:
        frozenset[str]
    """
    try:
        return frozenset(
            stopwords.words(NLTK_LANGUAGES[language])
            + _corporates
            + _stopwords.get(language, [])
            + list(_get_month_names(language))
            + list(_get_day_names(language))
        )

    except (OSError, KeyError):
        return frozenset()


def clean_text(text):
    """Scrubs text of any HTML tags and entities, punctuation and numbers.

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
    """Extracts all relevant keywords from text, removing any stopwords, HTML tags etc.

    Args:
        language (str): 2-char language code e.g. "en"
        text(str): text source

    Returns:
        str
    """
    if not (text := clean_text(text).casefold()):
        return []

    stopwords_for_language = get_stopwords(language)

    return [
        token
        for token in _lemmatized_tokens(text)
        if token and token not in stopwords_for_language
    ]


def _get_month_names(language):
    now = timezone.now()
    with translation.override(language):
        for month in range(1, 13):
            dt = datetime.date(now.year, month, 1)
            yield date_format(dt, "b").casefold()
            yield date_format(dt, "F").casefold()


def _get_day_names(language):
    now = timezone.now()
    with translation.override(language):
        for day in range(0, 7):
            dt = now + timedelta(days=day)
            yield date_format(dt, "D").casefold()
            yield date_format(dt, "l").casefold()


def _lemmatized_tokens(text):

    for token in _tokenizer.tokenize(text):
        try:
            yield _lemmatizer.lemmatize(token)
        except AttributeError:
            # threading issue:
            # 'WordNetCorpusReader' object has no attribute '_LazyCorpusLoader__args'
            pass
