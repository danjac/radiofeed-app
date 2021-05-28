from __future__ import annotations

import io
import mimetypes
import os
import uuid

from datetime import datetime
from functools import lru_cache
from urllib.parse import urlparse

import box
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

    result = box.Box(
        feedparser.parse(
            podcast.rss,
            etag=podcast.etag,
            modified=podcast.pub_date,
        ),
        default_box=True,
        default_box_none_transform=True,
    )

    items = [
        item for item in [with_audio(item) for item in result.entries] if item.audio
    ]

    if not items:
        return []

    feed = result.feed

    now = timezone.now()
    pub_date = parse_pub_date(feed, items)

    if pub_date is None:
        return []

    # timestamps
    podcast.etag = result.get("etag", "")
    podcast.last_updated = now
    podcast.pub_date = pub_date

    # description
    podcast.title = feed.title
    podcast.description = feed.description
    podcast.link = feed.link
    podcast.language = (feed.language or "en")[:2]
    podcast.explicit = feed.itunes_explicit or False
    podcast.creators = " ".join({author.name for author in feed.authors if author.name})

    parse_categories(podcast, feed, items)

    # reset errors
    podcast.sync_error = ""
    podcast.num_retries = 0

    if image := fetch_cover_image(podcast, feed):
        podcast.cover_image = image
        podcast.cover_image_date = now

    podcast.save()

    return sync_episodes(podcast, items)


def fetch_cover_image(podcast: Podcast, feed: box.Box) -> ImageFile | None:

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


def sync_episodes(podcast: Podcast, items: list[box.Box]) -> list[Episode]:
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
                duration=item.itunes_duration or "",
                explicit=item.itunes_explicit or False,
                keywords=" ".join([tag.term for tag in (item.tags or [])]),
            )
            for item in items
            if item.id not in guids
        ],
        ignore_conflicts=True,
    )


def parse_categories(podcast: Podcast, feed: box.Box, items: list[box.Box]) -> None:
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
    items: list[box.Box],
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


def parse_pub_date(feed: box.Box, items: list[box.Box]) -> datetime | None:
    if feed.published:
        return parse_date(feed.published)
    if feed.updated:
        return parse_date(feed.updated)
    pub_dates = [dt for dt in [parse_date(item.published) for item in items] if dt]
    if pub_dates:
        return max(pub_dates)
    return None


def with_audio(
    item: box.Box,
) -> box.Box:
    for link in (item.links or []) + (item.enclosures or []):
        if link.type.startswith("audio/") and link.href and link.rel == "enclosure":
            return item + box.Box(audio=link)
    return item
