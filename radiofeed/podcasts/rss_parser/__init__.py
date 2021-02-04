import datetime
from functools import lru_cache
from typing import Dict, List, Optional, cast

from django.utils import timezone

import feedparser
import requests
from bs4 import BeautifulSoup

from radiofeed.episodes.models import Episode

from ..models import Category, Podcast
from ..recommender.text_parser import extract_keywords
from .date_parser import parse_date
from .headers import get_headers
from .image import InvalidImageURL, fetch_image_from_url


class RssParser:
    def __init__(self, podcast: Podcast):
        self.podcast = podcast

    @classmethod
    def parse_from_podcast(cls, podcast) -> List[Episode]:
        return cls(podcast).parse()

    def parse(self) -> List[Episode]:

        try:
            # fetch etag and last modified
            head_response = requests.head(
                self.podcast.rss, headers=get_headers(), timeout=5
            )
            head_response.raise_for_status()
            headers = head_response.headers

            # if etag hasn't changed then we can skip
            etag = headers.get("ETag")
            if etag and etag == self.podcast.etag:
                return []

            response = requests.get(
                self.podcast.rss, headers=get_headers(), stream=True, timeout=5
            )
            response.raise_for_status()
        except requests.RequestException as e:
            self.podcast.sync_error = str(e)
            self.podcast.num_retries += 1
            self.podcast.save()
            raise

        data: Dict = feedparser.parse(response.content)
        feed: Dict = data["feed"]

        entries: List[Dict] = list(
            {
                e["id"]: cast(Dict, e) for e in data.get("entries", []) if "id" in e
            }.values()
        )

        if not entries:
            return []

        dates = [
            d
            for d in [
                parse_date(str(e["published"]) if "published" in e else None)
                for e in entries
            ]
            if d
        ]

        now: datetime.datetime = timezone.now()
        pub_date: Optional[datetime.datetime] = None

        if dates:
            pub_date = max([date for date in dates if date and date < now])

        do_update = (
            pub_date
            and self.podcast.last_updated is None
            or self.podcast.last_updated < pub_date
        )

        if not do_update:
            return []

        if etag:
            self.podcast.etag = etag

        self.podcast.title = feed["title"]
        self.podcast.description = feed["description"]
        self.podcast.language = feed.get("language", "en")[:2].strip().lower()
        self.podcast.explicit = bool(feed.get("itunes_explicit", False))

        if not self.podcast.cover_image:
            image_url = None

            # try itunes image first
            soup = BeautifulSoup(response.content, "lxml")
            itunes_img_tag = soup.find("itunes:image")
            if itunes_img_tag and "href" in itunes_img_tag.attrs:
                image_url = itunes_img_tag.attrs["href"]

            if not image_url:
                try:
                    image_url = feed["image"]["href"]
                except KeyError:
                    pass

            try:
                if image_url and (img := fetch_image_from_url(image_url)):
                    self.podcast.cover_image = img
            except InvalidImageURL:
                pass

        self.podcast.link = feed.get("link")

        categories_dct: Dict[str, Category] = get_categories_dict()

        keywords: List[str] = [t["term"] for t in feed.get("tags", [])]
        categories: List[Category] = [
            categories_dct[kw] for kw in keywords if kw in categories_dct
        ]

        self.podcast.last_updated = now
        self.podcast.pub_date = pub_date

        keywords = [kw for kw in keywords if kw not in categories_dct]
        self.podcast.keywords = " ".join(keywords)

        authors = set(
            [
                author["name"]
                for author in feed.get("authors", [])
                if "name" in author and author["name"]
            ]
        )

        self.podcast.authors = ", ".join(authors)
        self.podcast.extracted_text = self.extract_text(categories, entries)

        self.podcast.sync_error = ""
        self.podcast.num_retries = 0

        self.podcast.save()

        self.podcast.categories.set(categories)

        new_episodes = self.create_episodes_from_feed(entries)

        if new_episodes:
            self.podcast.pub_date = max(e.pub_date for e in new_episodes)
            self.podcast.save(update_fields=["pub_date"])

        return new_episodes

    def extract_text(self, categories: List[Category], entries: List[Dict]) -> str:
        """Extract keywords from text content for recommender"""
        text = " ".join(
            [
                self.podcast.title,
                self.podcast.description,
                self.podcast.keywords,
                self.podcast.authors,
            ]
            + [c.name for c in categories]
            + [e["title"] for e in entries][:6]
        )
        return " ".join([kw for kw in extract_keywords(self.podcast.language, text)])

    def create_episodes_from_feed(self, entries: List[Dict]) -> List[Episode]:
        """Parses new episodes from podcast feed."""
        guids = self.podcast.episode_set.values_list("guid", flat=True)
        entries = [entry for entry in entries if entry["id"] not in guids]

        episodes = [
            episode
            for episode in [self.create_episode_from_feed(entry) for entry in entries]
            if episode
        ]
        return Episode.objects.bulk_create(episodes, ignore_conflicts=True)

    def create_episode_from_feed(self, entry: Dict) -> Optional[Episode]:
        keywords = " ".join([t["term"] for t in entry.get("tags", [])])

        try:
            enclosure = [
                link
                for link in entry.get("links", [])
                if link.get("rel") == "enclosure"
                and link.get("type", "").startswith("audio/")
            ][0]
        except IndexError:
            return None

        if "url" not in enclosure or len(enclosure["url"]) > 500:
            return None

        try:
            description = (
                [
                    c["value"]
                    for c in entry.get("content", [])
                    if c.get("type") == "text/html"
                ]
                + [
                    entry[field]
                    for field in ("description", "summary", "subtitle")
                    if field in entry and entry[field]
                ]
            )[0]
        except IndexError:
            description = ""

        length: Optional[int] = None
        try:
            length = int(enclosure["length"])
        except (KeyError, ValueError):
            pass

        pub_date: Optional[datetime.datetime] = (
            parse_date(entry["published"]) if "published" in entry else None
        )
        if pub_date is None or pub_date > timezone.now():
            return None

        link = entry.get("link", "")
        if len(link) > 500:
            link = None

        return Episode(
            podcast=self.podcast,
            guid=entry["id"],
            title=entry["title"],
            link=link,
            duration=entry.get("itunes_duration", ""),
            explicit=bool(entry.get("itunes_explicit", False)),
            description=description,
            keywords=keywords,
            media_url=enclosure["url"],
            media_type=enclosure["type"],
            length=length,
            pub_date=pub_date,
        )


@lru_cache
def get_categories_dict() -> Dict[str, Category]:
    return {c.name: c for c in Category.objects.all()}
