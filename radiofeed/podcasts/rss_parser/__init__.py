import datetime
import logging

from functools import lru_cache
from typing import Dict, List, Optional

import requests

from django.utils import timezone
from pydantic import ValidationError

from radiofeed.episodes.models import Episode

from ..models import Category, Podcast
from ..recommender.text_parser import extract_keywords
from .headers import get_headers
from .image import InvalidImageURL, fetch_image_from_url
from .models import Feed, Item
from .xml_parser import parse_xml

logger = logging.getLogger(__name__)


class RssParser:
    def __init__(self, podcast: Podcast):
        self.podcast = podcast

    @classmethod
    def parse_from_podcast(cls, podcast, **kwargs) -> List[Episode]:
        return cls(podcast).parse(**kwargs)

    def parse(self, force_update: bool = False) -> List[Episode]:

        try:
            etag = self.fetch_etag(self.podcast.rss)
            if etag and etag == self.podcast.etag and not force_update:
                return []
            feed = self.fetch_rss_feed()
        except (ValidationError, requests.RequestException) as e:
            self.podcast.sync_error = str(e)
            self.podcast.num_retries += 1
            self.podcast.save()
            return []

        if self.sync_podcast(feed, etag, force_update):
            return self.sync_episodes(feed)

        return []

    def sync_podcast(self, feed: Feed, etag: Optional[str], force_update: bool) -> bool:

        if not (pub_date := self.get_pub_date(feed)):
            return False

        do_update = force_update or (
            self.podcast.last_updated is None or self.podcast.last_updated < pub_date
        )

        if not do_update:
            return False

        if etag:
            self.podcast.etag = etag

        self.podcast.title = feed.title
        self.podcast.description = feed.description
        self.podcast.link = feed.link
        self.podcast.language = feed.language
        self.podcast.explicit = feed.explicit
        self.podcast.last_updated = timezone.now()
        self.podcast.pub_date = pub_date

        categories = self.extract_categories(feed)

        self.podcast.authors = ", ".join(feed.authors)
        self.podcast.keywords = " ".join(self.extract_keywords(feed))
        self.podcast.extracted_text = self.extract_text(feed, categories)
        self.podcast.sync_error = ""
        self.podcast.num_retries = 0

        self.sync_cover_image(feed.image)

        self.podcast.save()

        self.podcast.categories.set(categories)

        return True

    def sync_cover_image(self, image_url: Optional[str]) -> None:
        if not image_url:
            return

        try:
            etag = self.fetch_etag(image_url)
        except requests.RequestException:
            return

        if not self.podcast.cover_image or etag != self.podcast.cover_image_etag:
            try:
                if image_url := fetch_image_from_url(image_url):
                    self.podcast.cover_image = image_url
                    self.podcast.cover_image_etag = etag or ""
            except InvalidImageURL:
                pass

    def sync_episodes(self, feed: Feed) -> List[Episode]:
        new_episodes = self.create_episodes_from_feed(feed)

        if new_episodes:
            self.podcast.pub_date = max(e.pub_date for e in new_episodes)
            self.podcast.save(update_fields=["pub_date"])

        return new_episodes

    def fetch_etag(self, url: str) -> Optional[str]:
        # fetch etag and last modified
        head_response = requests.head(url, headers=get_headers(), timeout=5)
        head_response.raise_for_status()
        headers = head_response.headers
        return headers.get("ETag")

    def fetch_rss_feed(self) -> Feed:
        response = requests.get(
            self.podcast.rss, headers=get_headers(), stream=True, timeout=5
        )
        response.raise_for_status()
        return parse_xml(response.content)

    def extract_categories(self, feed: Feed) -> List[Category]:
        categories_dct = get_categories_dict()

        return [
            categories_dct[name] for name in feed.categories if name in categories_dct
        ]

    def extract_keywords(self, feed: Feed) -> List[str]:
        categories_dct = get_categories_dict()
        return [name for name in feed.categories if name not in categories_dct]

    def extract_text(self, feed: Feed, categories: List[Category]) -> str:
        """Extract keywords from text content for recommender"""
        text = " ".join(
            [
                self.podcast.title,
                self.podcast.description,
                self.podcast.keywords,
                self.podcast.authors,
            ]
            + [c.name for c in categories]
            + [item.title for item in feed.items][:6]
        )
        return " ".join([kw for kw in extract_keywords(self.podcast.language, text)])

    def get_pub_date(self, feed: Feed) -> Optional[datetime.datetime]:
        now = timezone.now()
        try:
            return max([item.pub_date for item in feed.items if item.pub_date < now])
        except ValueError:
            return None

    def create_episodes_from_feed(self, feed: Feed) -> List[Episode]:
        """Parses new episodes from podcast feed."""
        guids = self.podcast.episode_set.values_list("guid", flat=True)
        return Episode.objects.bulk_create(
            [
                self.create_episode_from_item(item)
                for item in feed.items
                if item.guid not in guids
            ],
            ignore_conflicts=True,
        )

    def create_episode_from_item(self, item: Item) -> Episode:

        return Episode(
            podcast=self.podcast,
            pub_date=item.pub_date,
            guid=item.guid,
            title=item.title,
            duration=item.duration,
            explicit=item.explicit,
            description=item.description,
            keywords=item.keywords,
            media_url=item.audio.url,
            media_type=item.audio.type,
            length=item.audio.length,
        )


@lru_cache
def get_categories_dict() -> Dict[str, Category]:
    return {c.name: c for c in Category.objects.all()}
