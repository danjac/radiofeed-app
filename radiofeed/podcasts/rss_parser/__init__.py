import datetime
import logging
from functools import lru_cache
from typing import Dict, List, Optional

from django.utils import timezone

import requests

from radiofeed.episodes.models import Episode

from ..models import Category, Podcast
from ..recommender.text_parser import extract_keywords
from .headers import get_headers
from .image import InvalidImageURL, fetch_image_from_url
from .xml_parser import Feed, Item, parse_xml

logger = logging.getLogger(__name__)


class RssParser:
    def __init__(self, podcast: Podcast):
        self.podcast = podcast

    @classmethod
    def parse_from_podcast(cls, podcast) -> List[Episode]:
        return cls(podcast).parse()

    def parse(self) -> List[Episode]:

        try:
            etag = self.fetch_etag()
            if etag and etag == self.podcast.etag:
                self.debug("Matching etag, no update")
                return []
            xml = self.fetch_xml()
        except requests.RequestException as e:
            self.podcast.sync_error = str(e)
            self.podcast.num_retries += 1
            self.podcast.save()
            raise

        feed = parse_xml(xml)

        if feed is None or not feed.items:
            self.error("Feed is empty")
            return []

        pub_date = self.get_pub_date(feed)
        if not pub_date:
            self.debug("No recent pub date or new episodes")
            return []

        do_update: bool = (
            self.podcast.last_updated is None or self.podcast.last_updated < pub_date
        )

        if not do_update:
            self.debug("No recent pub date or new episodes")
            return []

        if etag:
            self.podcast.etag = etag

        self.podcast.title = feed.title
        self.podcast.description = feed.description
        self.podcast.link = feed.link
        self.podcast.language = (feed.language or "en")[:2].strip().lower()
        self.podcast.explicit = feed.explicit
        self.podcast.last_updated = timezone.now()
        self.podcast.pub_date = pub_date

        if not self.podcast.cover_image:
            try:
                if feed.image and (img := fetch_image_from_url(feed.image)):
                    self.podcast.cover_image = img
            except InvalidImageURL:
                pass

        categories_dct = get_categories_dict()

        categories = [
            categories_dct[name] for name in feed.categories if name in categories_dct
        ]

        keywords = [name for name in feed.categories if name not in categories_dct]
        self.podcast.keywords = " ".join(keywords)

        self.podcast.authors = ", ".join(feed.authors)
        self.podcast.extracted_text = self.extract_text(feed, categories)

        self.podcast.sync_error = ""
        self.podcast.num_retries = 0

        self.podcast.save()

        self.podcast.categories.set(categories)

        new_episodes = self.create_episodes_from_feed(feed)

        if new_episodes:
            self.podcast.pub_date = max(e.pub_date for e in new_episodes)
            self.podcast.save(update_fields=["pub_date"])

        self.debug(f"{len(new_episodes)} new episode(s)")
        return new_episodes

    def fetch_etag(self) -> Optional[str]:
        # fetch etag and last modified
        head_response = requests.head(
            self.podcast.rss, headers=get_headers(), timeout=5
        )
        head_response.raise_for_status()
        headers = head_response.headers
        return headers.get("ETag")

    def fetch_xml(self) -> bytes:
        response = requests.get(
            self.podcast.rss, headers=get_headers(), stream=True, timeout=5
        )
        response.raise_for_status()
        return response.content

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
            link=item.link[:500],
            duration=item.duration,
            explicit=item.explicit,
            description=item.description,
            keywords=item.keywords,
            media_url=item.audio.url,
            media_type=item.audio.type,
            length=item.audio.length,
        )

    def debug(self, message: str):
        logger.debug(f"{self.podcast}:{self.podcast.id}:{message}")

    def error(self, message: str):
        logger.error(f"{self.podcast}:{self.podcast.id}:{message}")


@lru_cache
def get_categories_dict() -> Dict[str, Category]:
    return {c.name: c for c in Category.objects.all()}
