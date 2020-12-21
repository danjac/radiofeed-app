# Standard Library
import re
from functools import lru_cache

# Django
from django.template.defaultfilters import striptags

# Third Party Libraries
from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tokenize import RegexpTokenizer

# RadioFeed
from radiofeed.common.html import stripentities

# Local
from .stopwords import STOPWORDS

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

tokenizer = RegexpTokenizer(r"\w+")
lemmatizer = WordNetLemmatizer()


@lru_cache()
def get_stopwords(language):
    try:
        return stopwords.words(NLTK_LANGUAGES[language]) + STOPWORDS.get(language, [])
    except KeyError:
        return []


def clean_text(text):
    """Remove HTML tags and entities, punctuation and numbers."""
    text = stripentities(striptags(text.strip()))
    text = re.sub(r"([^\s\w]|_:.?-)+", "", text)
    text = re.sub(r"[0-9]+", "", text)
    return text


def extract_keywords(language, text):
    text = clean_text(text).lower()

    if not text:
        return []

    tokens = [lemmatizer.lemmatize(token) for token in tokenizer.tokenize(text)]

    stopwords = get_stopwords(language)

    return [token for token in tokens if token and token not in stopwords]


def extract_text(podcast, categories, episodes):
    """Extracts keywords from podcast description fields, categories
    and recent episodes."""
    text = " ".join(
        [podcast.title, podcast.description, podcast.keywords, podcast.authors,]
        + [c.name for c in categories]
        + [e.title for e in episodes][:6]
    )
    return " ".join([kw for kw in extract_keywords(podcast.language, text)])
