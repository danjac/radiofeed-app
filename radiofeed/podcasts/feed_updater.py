from __future__ import annotations

import dataclasses
import functools
import hashlib
import http
import itertools
import secrets

from typing import Generator, Iterable

import requests

from django.db import transaction
from django.utils import timezone
from django.utils.http import http_date, quote_etag

from radiofeed.episodes.models import Episode
from radiofeed.podcasts.models import Category, Podcast
from radiofeed.podcasts.parsers import date_parser, rss_parser, text_parser

ACCEPT_HEADER = "application/atom+xml,application/rdf+xml,application/rss+xml,application/x-netcdf,application/xml;q=0.9,text/xml;q=0.2,*/*;q=0.1"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]


class NotModified(requests.RequestException):
    ...


class DuplicateFeed(requests.RequestException):
    ...


class FeedUpdater:
    def __init__(self, podcast: Podcast):
        self.podcast = podcast

    @transaction.atomic
    def update(self) -> bool:
        try:
            return self.handle_success(*self.parse_rss())

        except Exception as e:
            return self.handle_failure(e)

    def handle_success(
        self,
        response: requests.Response,
        feed: rss_parser.Feed,
        content_hash: str,
    ) -> bool:

        # taxonomy
        categories_dct = get_categories_dict()

        categories = [
            categories_dct[category]
            for category in feed.categories
            if category in categories_dct
        ]

        self.save_podcast(
            active=not feed.complete,
            content_hash=content_hash,
            rss=response.url,
            etag=response.headers.get("ETag", ""),
            http_status=response.status_code,
            modified=date_parser.parse_date(response.headers.get("Last-Modified")),
            pub_date=feed.latest_pub_date,
            title=feed.title,
            cover_url=feed.cover_url,
            description=feed.description,
            explicit=feed.explicit,
            funding_text=feed.funding_text,
            funding_url=feed.funding_url,
            language=feed.language,
            link=feed.link,
            owner=feed.owner,
            extracted_text=self.extract_text(feed, categories),
            keywords=" ".join(
                category
                for category in feed.categories
                if category not in categories_dct
            ),
        )

        # categories
        self.podcast.categories.set(categories)  # type: ignore

        # episodes
        self.sync_episodes(feed)

        return True

    def handle_failure(self, e: Exception) -> bool:
        try:
            http_status = e.response.status_code  # type: ignore
        except AttributeError:
            http_status = None

        match e:
            case NotModified():
                active = True
            case rss_parser.RssParserError() | DuplicateFeed():
                active = False
            case requests.RequestException():
                active = http_status not in (
                    http.HTTPStatus.FORBIDDEN,
                    http.HTTPStatus.GONE,
                    http.HTTPStatus.NOT_FOUND,
                    http.HTTPStatus.UNAUTHORIZED,
                )
            case _:
                raise

        self.save_podcast(active=active, http_status=http_status)
        return False

    def save_podcast(self, **fields):
        now = timezone.now()
        Podcast.objects.filter(pk=self.podcast.id).update(
            updated=now,
            parsed=now,
            queued=None,
            **fields,
        )

    def parse_rss(
        self,
    ) -> tuple[requests.Response, rss_parser.Feed, str]:

        response = requests.get(
            self.podcast.rss,
            headers=self.get_feed_headers(),
            allow_redirects=True,
            timeout=10,
        )

        response.raise_for_status()

        if response.status_code == http.HTTPStatus.NOT_MODIFIED:
            raise NotModified(response=response)

        # check if another feed already has new URL
        if (
            response.url != self.podcast.rss
            and Podcast.objects.filter(rss=response.url).exists()
        ):
            raise DuplicateFeed(response=response)

        # check if content has changed (feed is not checking etag etc)
        if (
            content_hash := make_content_hash(response.content)
        ) == self.podcast.content_hash:
            raise NotModified(response=response)

        # check if another feed has exact same content
        if (
            Podcast.objects.exclude(pk=self.podcast.id).filter(
                content_hash=content_hash, active=True
            )
        ).exists():
            raise DuplicateFeed(response=response)

        return response, rss_parser.parse_rss(response.content), content_hash

    def sync_episodes(self, feed: rss_parser.Feed, batch_size: int = 100) -> None:
        """Remove any episodes no longer in feed, update any current and
        add new"""

        qs = Episode.objects.filter(podcast=self.podcast)

        # remove any episodes that may have been deleted on the podcast
        qs.exclude(guid__in=[item.guid for item in feed.items]).delete()

        # determine new/current items based on presence of guid

        guids = dict(qs.values_list("guid", "pk"))

        for_insert = []

        # use set for update to prevent duplicates
        for_update = set()

        for item in feed.items:

            episode = Episode(
                pk=guids.get(item.guid),
                podcast=self.podcast,
                **dataclasses.asdict(item),
            )

            if episode.pk:
                for_update.add(episode)
            else:
                for_insert.append(episode)

        # update existing content

        for batch in batcher(for_update, batch_size):
            Episode.fast_update_objects.fast_update(
                batch,
                fields=[
                    "cover_url",
                    "description",
                    "duration",
                    "episode",
                    "episode_type",
                    "explicit",
                    "keywords",
                    "length",
                    "media_type",
                    "media_url",
                    "pub_date",
                    "season",
                    "title",
                ],
            )

        # add new episodes

        for batch in batcher(for_insert, batch_size):
            Episode.objects.bulk_create(batch, ignore_conflicts=True)

    def extract_text(self, feed: rss_parser.Feed, categories: list[Category]) -> str:
        text = " ".join(
            value
            for value in [
                self.podcast.title,
                self.podcast.description,
                self.podcast.keywords,
                self.podcast.owner,
            ]
            + [c.name for c in categories]
            + [item.title for item in feed.items][:6]
            if value
        )
        return " ".join(text_parser.extract_keywords(self.podcast.language, text))

    def get_feed_headers(self) -> dict[str, str]:
        headers = {
            "Accept": ACCEPT_HEADER,
            "User-Agent": get_user_agent(),
        }

        if self.podcast.etag:
            headers["If-None-Match"] = quote_etag(self.podcast.etag)
        if self.podcast.modified:
            headers["If-Modified-Since"] = http_date(self.podcast.modified.timestamp())
        return headers


@functools.lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")


def batcher(iterable: Iterable, batch_size: int) -> Generator[list, None, None]:
    iterator = iter(iterable)
    while batch := list(itertools.islice(iterator, batch_size)):
        yield batch


def make_content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def get_user_agent() -> str:
    return secrets.choice(USER_AGENTS)
