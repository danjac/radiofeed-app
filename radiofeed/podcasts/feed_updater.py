from __future__ import annotations

import dataclasses
import functools
import hashlib
import http
import itertools
import secrets

from datetime import timedelta
from typing import Generator, Iterable

import requests

from django.db import transaction
from django.db.models import Count, F, Q, QuerySet
from django.db.models.functions import ExtractDay
from django.utils import timezone
from django.utils.http import http_date, quote_etag
from django_rq import get_queue, job

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
def update(podcast_id: int, **kwargs) -> Result:
    try:
        return FeedUpdater(Podcast.objects.get(pk=podcast_id)).update(**kwargs)
    except Podcast.DoesNotExist:
        return Result()


def enqueue(*podcast_ids: int, **job_kwargs) -> None:

    queue = get_queue("feeds")

    Podcast.objects.filter(pk__in=podcast_ids).update(queued=timezone.now())

    for podcast_id in podcast_ids:
        queue.enqueue(update, args=(podcast_id,), **job_kwargs)


def enqueue_scheduled_feeds(limit: int, **job_kwargs) -> frozenset[int]:

    podcast_ids = frozenset(
        itertools.islice(
            get_scheduled_feeds().values_list("pk", flat=True).distinct(),
            limit,
        )
    )

    enqueue(*podcast_ids, **job_kwargs)
    return podcast_ids


class FeedUpdater:
    def __init__(self, podcast: Podcast):
        self.podcast = podcast

    @transaction.atomic
    def update(self) -> Result:
        try:
            return self.handle_success(*self.parse_content())

        except Exception as e:
            return self.handle_failure(e)

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

    def handle_success(
        self,
        response: requests.Response,
        content_hash: str,
        feed: rss_parser.Feed,
        items: list[rss_parser.Item],
    ) -> Result:

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

        return Result.from_podcast(self.podcast)

    def handle_failure(self, e: Exception) -> Result:

        result = Result.from_exception(e)

        now = timezone.now()

        errors = self.podcast.errors + 1 if result.error else 0
        active = result.active and errors < 3

        Podcast.objects.filter(pk=self.podcast.id).update(
            active=active,
            result=result.result,
            http_status=result.http_status,
            errors=errors,
            parsed=now,
            updated=now,
            queued=None,
        )

        return result

    def sync_episodes(
        self, items: list[rss_parser.Item], batch_size: int = 100
    ) -> None:
        """Remove any episodes no longer in feed, update any current and
        add new"""

        qs = Episode.objects.filter(podcast=self.podcast)

        # remove any episodes that may have been deleted on the podcast
        qs.exclude(guid__in=[item.guid for item in items]).delete()

        # determine new/current items based on presence of guid

        guids = dict(qs.values_list("guid", "pk"))

        episodes = [
            Episode(
                pk=guids.get(item.guid),
                podcast=self.podcast,
                **dataclasses.asdict(item),
            )
            for item in items
        ]

        # update existing content

        for batch in batcher(
            filter(lambda episode: episode.guid in guids, episodes),
            batch_size,
        ):
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

        # add new episodes

        for batch in batcher(
            filter(lambda episode: episode.guid not in guids, episodes),
            batch_size,
        ):
            Episode.objects.bulk_create(batch, ignore_conflicts=True)

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


@dataclasses.dataclass
class Result:

    result: str | None = None
    http_status: int | None = None

    @classmethod
    def from_podcast(cls, podcast: Podcast) -> Result:
        return cls(result=podcast.result, http_status=podcast.http_status)  # type: ignore

    @classmethod
    def from_exception(cls, e: Exception) -> Result:
        try:
            http_status = e.response.status_code  # type: ignore
        except AttributeError:
            http_status = None

        result = None

        match e:

            case NotModified():
                result = Podcast.Result.NOT_MODIFIED

            case DuplicateFeed():
                result = Podcast.Result.DUPLICATE_FEED

            case requests.HTTPError():
                result = (
                    Podcast.Result.REMOVED
                    if http_status == http.HTTPStatus.GONE
                    else Podcast.Result.HTTP_ERROR
                )

            case requests.RequestException():
                result = Podcast.Result.NETWORK_ERROR

            case rss_parser.RssParserError():
                result = Podcast.Result.INVALID_RSS

            case _:
                raise

        return cls(result=result, http_status=http_status)  # type: ignore

    def __bool__(self) -> bool:
        return self.result == Podcast.Result.SUCCESS

    @property
    def active(self) -> bool:
        return self.result not in (
            Podcast.Result.DUPLICATE_FEED,
            Podcast.Result.REMOVED,
        )

    @property
    def error(self) -> bool:
        return self.result in (
            Podcast.Result.HTTP_ERROR,
            Podcast.Result.INVALID_RSS,
            Podcast.Result.NETWORK_ERROR,
        )


def get_scheduled_feeds() -> QuerySet[Podcast]:
    now = timezone.now()

    return (
        Podcast.objects.annotate(
            subscribers=Count("subscription"),
            days_since_last_pub_date=ExtractDay(now - F("pub_date")),
        )
        .filter(
            Q(
                parsed__isnull=True,
            )
            | Q(
                pub_date__isnull=True,
            )
            | Q(
                days_since_last_pub_date__lt=1,
                parsed__lt=now - timedelta(hours=1),
            )
            | Q(
                days_since_last_pub_date__gt=24,
                parsed__lt=now - timedelta(hours=24),
            )
            | Q(
                days_since_last_pub_date__range=(1, 24),
                parsed__lt=now - timedelta(hours=1) * F("days_since_last_pub_date"),
            ),
            queued__isnull=True,
            active=True,
        )
        .order_by(
            F("subscribers").desc(),
            F("promoted").desc(),
            F("parsed").asc(nulls_first=True),
            F("pub_date").desc(nulls_first=True),
        )
    )


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
