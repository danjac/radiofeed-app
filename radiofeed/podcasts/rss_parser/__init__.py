import datetime
import logging

from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import requests

from django.core.files.images import ImageFile
from django.utils import timezone
from pydantic import ValidationError

from radiofeed.episodes.models import Episode

from ..models import Category, Podcast
from ..recommender.text_parser import extract_keywords
from .feed_parser import parse_feed
from .headers import get_headers
from .image import InvalidImageURL, fetch_image_from_url
from .models import Feed, Item

logger = logging.getLogger(__name__)


def parse_rss(podcast: Podcast, force_update: bool = False) -> int:
    """Parses RSS feed for podcast. If force_update is provided will
    re-fetch all podcast info, episodes etc even if podcast does not
    have new content (provided a valid feed is available).

    Returns number of new epiosdes.
    """

    feed, etag = fetch_rss_feed(podcast, force_update)
    if feed is None:
        return 0

    if sync_podcast(podcast, feed, etag, force_update):
        return sync_episodes(podcast, feed)

    return 0


def sync_podcast(
    podcast: Podcast,
    feed: Feed,
    etag: str,
    force_update: bool,
) -> bool:

    pub_date = extract_pub_date(feed)

    if not do_update(podcast, etag, pub_date, force_update):
        return False

    podcast.etag = etag
    podcast.pub_date = pub_date

    podcast.title = feed.title
    podcast.description = feed.description
    podcast.link = feed.link
    podcast.language = feed.language
    podcast.explicit = feed.explicit

    podcast.last_updated = timezone.now()

    categories = extract_categories(feed)

    podcast.authors = ", ".join(feed.authors)

    podcast.keywords = extract_keywords_from_feed(feed)
    podcast.extracted_text = extract_text(podcast, feed, categories)

    podcast.parse_error = ""
    podcast.num_retries = 0

    if not podcast.cover_image:
        podcast.cover_image = extract_cover_image(feed)

    podcast.save()

    podcast.categories.set(categories)

    return True


def sync_episodes(podcast: Podcast, feed: Feed) -> int:
    new_episodes = create_episodes_from_feed(podcast, feed)

    if new_episodes:
        podcast.pub_date = max(e.pub_date for e in new_episodes)
        podcast.save(update_fields=["pub_date"])

    return len(new_episodes)


def do_update(
    podcast: Podcast,
    etag: str,
    pub_date: Optional[datetime.datetime],
    force_update: bool,
) -> bool:
    if not pub_date:
        return False

    if force_update:
        return True

    return podcast.last_updated is None or podcast.last_updated < pub_date


def fetch_etag(url: str) -> str:
    # fetch etag and last modified
    head_response = requests.head(url, headers=get_headers(), timeout=5)
    head_response.raise_for_status()
    headers = head_response.headers
    return headers.get("ETag", "")


def fetch_rss_feed(podcast: Podcast, force_update: bool) -> Tuple[Optional[Feed], str]:

    try:
        etag = fetch_etag(podcast.rss)
        if etag and etag == podcast.etag and not force_update:
            return None, etag

        response = requests.get(
            podcast.rss, headers=get_headers(), stream=True, timeout=5
        )
        response.raise_for_status()
        return parse_feed(response.content), etag
    except (ValidationError, requests.RequestException) as e:
        podcast.parse_error = str(e)
        podcast.num_retries += 1
        podcast.save()

    return None, ""


def extract_pub_date(feed: Feed) -> Optional[datetime.datetime]:
    now = timezone.now()
    try:
        return max([item.pub_date for item in feed.items if item.pub_date < now])
    except ValueError:
        return None


def extract_categories(feed: Feed) -> List[Category]:
    categories_dct = get_categories_dict()
    return [categories_dct[name] for name in feed.categories if name in categories_dct]


def extract_keywords_from_feed(feed: Feed) -> str:
    categories_dct = get_categories_dict()
    return " ".join([name for name in feed.categories if name not in categories_dct])


def extract_text(podcast: Podcast, feed: Feed, categories: List[Category]) -> str:
    """Extract keywords from text content for recommender"""
    text = " ".join(
        [
            podcast.title,
            podcast.description,
            podcast.keywords,
            podcast.authors,
        ]
        + [c.name for c in categories]
        + [item.title for item in feed.items][:6]
    )
    return " ".join([kw for kw in extract_keywords(podcast.language, text)])


def extract_cover_image(feed: Feed) -> Optional[ImageFile]:
    if not feed.image:
        return None

    try:
        return fetch_image_from_url(feed.image)
    except InvalidImageURL:
        pass

    return None


def create_episodes_from_feed(podcast: Podcast, feed: Feed) -> List[Episode]:
    """Parses new episodes from podcast feed."""
    guids = podcast.episode_set.values_list("guid", flat=True)
    return Episode.objects.bulk_create(
        [
            create_episode_from_item(podcast, item)
            for item in feed.items
            if item.guid not in guids
        ],
        ignore_conflicts=True,
    )


def create_episode_from_item(podcast: Podcast, item: Item) -> Episode:

    return Episode(
        podcast=podcast,
        pub_date=item.pub_date,
        guid=item.guid,
        title=item.title,
        duration=item.duration,
        explicit=item.explicit,
        description=item.description,
        keywords=item.keywords,
        link=item.link,
        media_url=item.audio.url,
        media_type=item.audio.type,
        length=item.audio.length,
    )


@lru_cache
def get_categories_dict() -> Dict[str, Category]:
    return {c.name: c for c in Category.objects.all()}
