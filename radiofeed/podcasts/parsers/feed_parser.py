from __future__ import annotations

import dataclasses
import functools
import hashlib
import http
import itertools
import secrets

import requests

from django.db import transaction
from django.utils import timezone
from django.utils.http import http_date, quote_etag
from django_rq import job

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


@job("feeds")
def parse_podcast_feed(podcast_id: int, **kwargs) -> bool:
    try:
        return FeedParser(Podcast.objects.get(pk=podcast_id)).parse(**kwargs)
    except Podcast.DoesNotExist:
        return False


class FeedParser:
    def __init__(self, podcast: Podcast):
        self.podcast = podcast

    @transaction.atomic
    def parse(self) -> bool:
        try:
            return self.handle_successful_update(*self.parse_content())

        except Exception as e:
            return self.handle_unsuccessful_update(e)

    def parse_content(
        self,
    ) -> tuple[requests.Response, str, rss_parser.Feed, list[rss_parser.Item]]:

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

        return response, content_hash, *rss_parser.parse_rss(response.content)

    def handle_successful_update(
        self,
        response: requests.Response,
        content_hash: str,
        feed: rss_parser.Feed,
        items: list[rss_parser.Item],
    ) -> bool:

        # feed status

        self.podcast.rss = response.url
        self.podcast.http_status = response.status_code
        self.podcast.etag = response.headers.get("ETag", "")
        self.podcast.modified = date_parser.parse_date(
            response.headers.get("Last-Modified")
        )

        self.podcast.parsed = timezone.now()
        self.podcast.queued = None
        self.podcast.result = self.podcast.Result.SUCCESS  # type: ignore
        self.podcast.content_hash = content_hash

        self.podcast.active = not feed.complete
        self.podcast.errors = 0

        pub_dates = [item.pub_date for item in items if item.pub_date]

        self.podcast.pub_date = max(pub_dates)

        # content

        for field in (
            "cover_url",
            "description",
            "explicit",
            "funding_text",
            "funding_url",
            "language",
            "link",
            "owner",
            "title",
        ):
            setattr(self.podcast, field, getattr(feed, field))

        # taxonomy
        categories_dct = get_categories_dict()

        categories = [
            categories_dct[category]
            for category in feed.categories
            if category in categories_dct
        ]
        self.podcast.keywords = " ".join(
            category for category in feed.categories if category not in categories_dct
        )
        self.podcast.extracted_text = self.extract_text(categories, items)

        self.podcast.categories.set(categories)  # type: ignore

        self.podcast.save()

        # episodes
        self.sync_episodes(items)

        return True

    def sync_episodes(self, items: list[rss_parser.Item]) -> None:
        """Remove any episodes no longer in feed, update any current and
        add new"""

        qs = Episode.objects.filter(podcast=self.podcast)

        # remove any episodes that may have been deleted on the podcast
        qs.exclude(guid__in=[item.guid for item in items]).delete()

        # determine new/current items
        guids_dct = dict(qs.values_list("guid", "pk"))

        # update existing content
        episodes = [
            Episode(
                pk=guids_dct.get(item.guid),
                podcast=self.podcast,
                **dataclasses.asdict(item),
            )
            for item in items
        ]

        guids = frozenset(guids_dct.keys())

        self.update_episodes(episodes, guids)
        self.create_episodes(episodes, guids)

    def create_episodes(self, episodes: list[Episode], guids: frozenset[str]) -> None:

        # new episodes
        for_create = iter(episodes)

        while True:
            batch = list(
                itertools.islice(
                    filter(
                        lambda episode: episode.guid not in guids,
                        for_create,
                    ),
                    100,
                )
            )
            if not batch:
                return

            Episode.objects.bulk_create(batch, ignore_conflicts=True)

    def update_episodes(self, episodes: list[Episode], guids: frozenset[str]) -> None:

        for_update = iter(episodes)

        while True:
            batch = list(
                itertools.islice(
                    filter(
                        lambda episode: episode.guid in guids,
                        for_update,
                    ),
                    100,
                )
            )
            if not batch:
                return
            Episode.objects.bulk_update(
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

    def extract_text(
        self, categories: list[Category], items: list[rss_parser.Item]
    ) -> str:
        text = " ".join(
            value
            for value in [
                self.podcast.title,
                self.podcast.description,
                self.podcast.keywords,
                self.podcast.owner,
            ]
            + [c.name for c in categories]
            + [item.title for item in items][:6]
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

    def handle_unsuccessful_update(self, e: Exception) -> bool:

        result = None
        active = True
        error = False

        try:
            http_status = e.response.status_code  # type: ignore
        except AttributeError:
            http_status = None

        match e:

            case NotModified():
                result = Podcast.Result.NOT_MODIFIED

            case DuplicateFeed():
                result = Podcast.Result.DUPLICATE_FEED
                active = False

            case requests.HTTPError():

                result = Podcast.Result.HTTP_ERROR
                active = error = http_status != http.HTTPStatus.GONE

            case requests.RequestException():

                result = Podcast.Result.NETWORK_ERROR
                error = True

            case rss_parser.RssParserError():

                result = Podcast.Result.INVALID_RSS
                error = True

            case _:
                raise

        now = timezone.now()

        errors = self.podcast.errors + 1 if error else 0
        active = active and errors < 3

        Podcast.objects.filter(pk=self.podcast.id).update(
            active=active,
            result=result,
            http_status=http_status,
            errors=errors,
            parsed=now,
            updated=now,
            queued=None,
        )

        return False


def make_content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def get_user_agent() -> str:
    return secrets.choice(USER_AGENTS)


@functools.lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")
