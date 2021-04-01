import re

from functools import lru_cache

from django.template.defaultfilters import striptags
from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tokenize import RegexpTokenizer

from audiotrails.template.html import stripentities

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
