from __future__ import annotations

import io
import mimetypes
import os
import uuid

from functools import lru_cache
from urllib.parse import urlparse

import feedparser
import requests

from django.core.exceptions import ValidationError
from django.core.files.images import ImageFile
from django.core.validators import validate_image_file_extension
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

from audiotrails.episodes.models import Episode
from audiotrails.podcasts.date_parser import parse_date
from audiotrails.podcasts.models import Category, Podcast
from audiotrails.podcasts.text_parser import extract_keywords

MAX_IMAGE_SIZE = 1000
THUMBNAIL_SIZE = 200


@lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")


def parse_feed(podcast: Podcast) -> list[Episode]:

    result = feedparser.parse(podcast.rss, etag=podcast.etag, modified=podcast.pub_date)

    # append an "audio" item for easier lookup

    items = [
        item
        for item in [
            feedparser.FeedParserDict({**item, "audio": get_audio_enclosure(item)})
            for item in result.entries
        ]
        if item.audio
    ]

    if not items:
        return []

    feed = result.feed

    now = timezone.now()

    # timestamps
    podcast.etag = result.get("etag", "")
    podcast.pub_date = parse_date(result.feed.published)
    podcast.last_updated = now

    # description
    podcast.title = feed.title
    podcast.description = feed.description
    podcast.link = feed.link
    podcast.language = feed.language
    podcast.explicit = feed.itunes_explicit
    podcast.creators = " ".join({author.name for author in feed.authors})

    parse_categories(podcast, feed, items)

    # reset errors
    podcast.sync_error = ""
    podcast.num_retries = 0

    if image := fetch_cover_image(podcast, feed):
        podcast.cover_image = image
        podcast.cover_image_date = now

    podcast.save()

    return sync_episodes(podcast, items)


def fetch_cover_image(
    podcast: Podcast, feed: feedparser.FeedParserDict
) -> ImageFile | None:

    if podcast.cover_image:
        return None

    try:
        response = requests.get(feed.image.href, timeout=5, stream=True)
    except (AttributeError, requests.RequestException):
        return None

    if (img := create_image_obj(response.content)) is None:
        return None

    image_file = ImageFile(img, name=make_filename(response))

    try:
        validate_image_file_extension(image_file)
    except ValidationError:
        return None

    return image_file


def sync_episodes(
    podcast: Podcast, items: list[feedparser.FeedParserDict]
) -> list[Episode]:
    episodes = Episode.objects.filter(podcast=podcast)

    # remove any episodes that may have been deleted on the podcast
    episodes.exclude(guid__in=[item.id for item in items]).delete()
    guids = episodes.values_list("guid", flat=True)

    return Episode.objects.bulk_create(
        [
            Episode(
                podcast=podcast,
                guid=item.id,
                title=item.title,
                description=item.description,
                link=item.link,
                media_url=item.audio.href,
                media_type=item.audio.type,
                length=item.audio.length or None,
                pub_date=parse_date(item.published),
                duration=item.get("itunes_duration", ""),
                explicit=item.get("itunes_explicit", False),
                keywords=" ".join([tag.term for tag in item.get("tags", [])]),
            )
            for item in items
            if item.id not in guids
        ],
        ignore_conflicts=True,
    )


def parse_categories(
    podcast: Podcast,
    feed: feedparser.FeedParserDict,
    items: list[feedparser.FeedParserDict],
) -> None:
    """Extract keywords from text content for recommender
    and map to categories"""
    categories_dct = get_categories_dict()

    tags = [tag.term for tag in feed.tags]

    categories = [categories_dct[name] for name in tags if name in categories_dct]

    podcast.keywords = " ".join(name for name in tags if name not in categories_dct)
    podcast.extracted_text = extract_text(podcast, categories, items)
    podcast.categories.set(categories)  # type: ignore


def extract_text(
    podcast: Podcast,
    categories: list[Category],
    items: list[feedparser.FeedParserDict],
) -> str:
    text = " ".join(
        [
            podcast.title,
            podcast.description,
            podcast.keywords,
            podcast.creators,
        ]
        + [c.name for c in categories]
        + [item.title for item in items][:6]
    )
    return " ".join(extract_keywords(podcast.language, text))


def make_filename(response: requests.Response) -> str:
    _, ext = os.path.splitext(urlparse(response.url).path)

    if ext is None:
        try:
            content_type = response.headers["Content-Type"].split(";")[0]
        except KeyError:
            content_type = mimetypes.guess_type(response.url)[0] or ""

        ext = mimetypes.guess_extension(content_type) or ""

    return uuid.uuid4().hex + ext


def create_image_obj(raw: bytes) -> Image:
    try:
        img = Image.open(io.BytesIO(raw))

        if img.height > MAX_IMAGE_SIZE or img.width > MAX_IMAGE_SIZE:
            img = img.resize((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.ANTIALIAS)

        # remove Alpha channel
        img = img.convert("RGB")

        fp = io.BytesIO()
        img.seek(0)
        img.save(fp, "PNG")

        return fp

    except (
        DecompressionBombError,
        UnidentifiedImageError,
    ):
        return None


def get_audio_enclosure(
    item: feedparser.FeedParserDict,
) -> feedparser.FeedParserDict | None:
    if not item.enclosures:
        return None
    for enc in item.enclosures:
        if enc.type.startswith("audio/") and enc.href:
            return enc
    return None
