from __future__ import annotations

import dataclasses
import functools
import hashlib
import http
import secrets

from datetime import timedelta

import attr
import requests

from django.db import transaction
from django.utils import timezone
from django.utils.http import http_date, quote_etag

from radiofeed.episodes.models import Episode
from radiofeed.podcasts.models import Category, Podcast
from radiofeed.podcasts.parsers import date_parser, rss_parser, text_parser

ACCEPT_HEADER = "application/atom+xml,application/rdf+xml,application/rss+xml,application/x-netcdf,application/xml;q=0.9,text/xml;q=0.2,*/*;q=0.1"

PARSE_ERROR_LIMIT = 3  # max errors before podcast is "dead"

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


@dataclasses.dataclass
class ParseResult:
    rss: str | None = None
    success: bool = False
    status: int | None = None
    result: str | None = None
    exception: Exception | None = None

    def __bool__(self) -> bool:
        return self.success

    def raise_exception(self) -> None:
        if self.exception:
            raise self.exception


@transaction.atomic
def parse_podcast_feed(podcast_id: int) -> ParseResult:

    try:
        return FeedParser(
            Podcast.objects.filter(active=True).get(pk=podcast_id)
        ).parse()

    except Podcast.DoesNotExist as e:
        return ParseResult(rss=None, success=False, exception=e)


class FeedParser:
    def __init__(self, podcast: Podcast):
        self.podcast = podcast

    def parse(self) -> ParseResult:
        try:
            return self.parse_hit(*self.parse_content())

        except NotModified as e:
            return self.parse_miss(
                result=Podcast.Result.NOT_MODIFIED,  # type: ignore
                status=e.response.status_code,
            )

        except DuplicateFeed as e:
            return self.parse_miss(
                result=Podcast.Result.DUPLICATE_FEED,  # type: ignore
                status=e.response.status_code,
                active=False,
            )

        except requests.HTTPError as e:

            if e.response.status_code == http.HTTPStatus.GONE:
                return self.parse_miss(
                    result=Podcast.Result.HTTP_ERROR,  # type: ignore
                    status=e.response.status_code,
                    active=False,
                )

            return self.parse_miss(
                result=Podcast.Result.HTTP_ERROR,  # type: ignore
                status=e.response.status_code,
                exception=e,
            )

        except requests.RequestException as e:
            return self.parse_miss(
                result=Podcast.Result.NETWORK_ERROR,  # type: ignore
                exception=e,
            )

        except rss_parser.RssParserError as e:
            return self.parse_miss(
                result=Podcast.Result.INVALID_RSS,  # type: ignore
                exception=e,
            )

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

    def parse_hit(
        self,
        response: requests.Response,
        content_hash: str,
        feed: rss_parser.Feed,
        items: list[rss_parser.Item],
    ) -> ParseResult:

        # feed status

        self.podcast.rss = response.url
        self.podcast.http_status = response.status_code
        self.podcast.etag = response.headers.get("ETag", "")
        self.podcast.modified = date_parser.parse_date(
            response.headers.get("Last-Modified")
        )

        # parsing result

        self.podcast.parsed = timezone.now()
        self.podcast.result = self.podcast.Result.SUCCESS  # type: ignore
        self.podcast.content_hash = content_hash
        self.podcast.exception = ""

        self.podcast.active = not feed.complete
        self.podcast.errors = 0

        pub_date = max([item.pub_date for item in items if item.pub_date])

        self.podcast.refresh_interval = (
            self.decrement_refresh_interval()
            if self.podcast.pub_date is None or pub_date > self.podcast.pub_date
            else self.increment_refresh_interval()
        )

        self.podcast.pub_date = pub_date

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
        self.parse_episodes(items)

        return ParseResult(
            rss=self.podcast.rss,
            success=True,
            status=response.status_code,
        )

    def parse_miss(
        self,
        *,
        active: bool = True,
        status: int | None = None,
        result: Podcast.Result | None = None,
        exception: Exception | None = None,
    ) -> ParseResult:

        now = timezone.now()

        errors = self.podcast.errors + 1 if exception else 0
        active = active and errors < PARSE_ERROR_LIMIT

        Podcast.objects.filter(pk=self.podcast.id).update(
            refresh_interval=self.increment_refresh_interval(),
            active=active,
            result=result,
            http_status=status,
            errors=errors,
            parsed=now,
            updated=now,
        )

        return ParseResult(
            rss=self.podcast.rss,
            success=False,
            status=status,
            exception=exception,
            result=result.value if result else None,
        )

    def parse_episodes(
        self, items: list[rss_parser.Item], batch_size: int = 500
    ) -> None:
        """Remove any episodes no longer in feed, update any current and
        add new"""

        qs = Episode.objects.filter(podcast=self.podcast)

        # remove any episodes that may have been deleted on the podcast
        qs.exclude(guid__in=[item.guid for item in items]).delete()

        # determine new/current items
        guids = dict(qs.values_list("guid", "pk"))

        episodes = [
            Episode(pk=guids.get(item.guid), podcast=self.podcast, **attr.asdict(item))
            for item in items
        ]

        # update existing content

        Episode.objects.bulk_update(
            [episode for episode in episodes if episode.guid in guids],
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
            batch_size=batch_size,
        )

        # new episodes

        Episode.objects.bulk_create(
            [episode for episode in episodes if episode.guid not in guids],
            ignore_conflicts=True,
            batch_size=batch_size,
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

    def decrement_refresh_interval(self) -> timedelta:
        seconds = self.podcast.refresh_interval.total_seconds()

        return max(
            timedelta(seconds=seconds - (seconds * 0.1)),
            timedelta(hours=1),
        )

    def increment_refresh_interval(self) -> timedelta:
        seconds = self.podcast.refresh_interval.total_seconds()

        return min(
            timedelta(seconds=seconds + (seconds * 0.1)),
            timedelta(hours=6),
        )


def make_content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def get_user_agent() -> str:
    return secrets.choice(USER_AGENTS)


@functools.lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")
