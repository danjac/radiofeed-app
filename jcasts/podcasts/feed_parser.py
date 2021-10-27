from __future__ import annotations

import http
import multiprocessing
import secrets
import statistics
import traceback

from datetime import datetime, timedelta
from functools import lru_cache

import attr
import requests

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.http import http_date, quote_etag
from django_rq import job

from jcasts.episodes.models import Episode
from jcasts.podcasts import date_parser, rss_parser, text_parser
from jcasts.podcasts.models import Category, Podcast

ACCEPT_HEADER = "application/atom+xml,application/rdf+xml,application/rss+xml,application/x-netcdf,application/xml;q=0.9,text/xml;q=0.2,*/*;q=0.1"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]

MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=30)


class NotModified(requests.RequestException):
    ...


class DuplicateFeed(requests.RequestException):
    ...


@attr.s(kw_only=True)
class ParseResult:
    rss: str | None = attr.ib()
    success: bool = attr.ib(default=False)
    status: int | None = attr.ib(default=None)
    result: str | None = attr.ib(default=None)
    exception: Exception | None = attr.ib(default=None)

    def __bool__(self):
        return self.success

    def raise_exception(self):
        if self.exception:
            raise self.exception


def schedule_podcast_feeds(frequency: timedelta) -> None:
    """
    Schedules feeds for update.
    """

    # rough estimate: takes 2 seconds per update
    limit = multiprocessing.cpu_count() * round(frequency.total_seconds() / 2)

    # ensure that we do not parse feeds already polled within the time period
    qs = (
        Podcast.objects.active()
        .scheduled(frequency)
        .with_followed()
        .distinct()
        .order_by(
            F("polled").asc(nulls_first=True),
            F("pub_date").desc(nulls_first=True),
        )
    )

    # prioritize any followed or promoted podcasts
    primary = qs.filter(Q(followed=True) | Q(promoted=True))
    secondary = qs.filter(followed=False, promoted=False)

    remainder = 0
    now = timezone.now()

    for (qs, ratio) in [
        (primary, 0.5),
        (secondary.fresh(), 0.3),
        (secondary.stale(), 0.2),
    ]:

        remainder += round(limit * ratio)

        podcast_ids = list(qs[:remainder].values_list("pk", flat=True))

        # process the feeds

        Podcast.objects.filter(pk__in=podcast_ids).update(queued=now)

        for podcast_id in podcast_ids:
            parse_podcast_feed.delay(podcast_id)

        remainder -= len(podcast_ids)


@job("feeds")
@transaction.atomic
def parse_podcast_feed(podcast_id: int) -> ParseResult:

    try:
        podcast = Podcast.objects.get(pk=podcast_id, active=True)
        response = get_feed_response(podcast)
        feed, items = rss_parser.parse_rss(response.content)

        if not is_feed_changed(podcast, feed):
            raise NotModified(response=response)

        return parse_success(podcast, response, feed, items)

    except Podcast.DoesNotExist as e:
        return ParseResult(rss=None, success=False, exception=e)

    except NotModified as e:
        return parse_failure(
            podcast,
            status=e.response.status_code,
            result=Podcast.Result.NOT_MODIFIED,
        )

    except DuplicateFeed as e:
        return parse_failure(
            podcast,
            active=False,
            result=Podcast.Result.DUPLICATE_FEED,
            status=e.response.status_code,
        )

    except requests.HTTPError as e:
        return parse_failure(
            podcast,
            result=Podcast.Result.HTTP_ERROR,
            status=e.response.status_code,
            active=False,
        )

    except requests.RequestException as e:
        return parse_failure(
            podcast,
            exception=e,
            result=Podcast.Result.NETWORK_ERROR,
            tb=traceback.format_exc(),
        )

    except rss_parser.RssParserError as e:
        return parse_failure(
            podcast,
            result=Podcast.Result.INVALID_RSS,
            status=response.status_code,
            active=False,
            exception=e,
            tb=traceback.format_exc(),
        )


def get_feed_response(podcast: Podcast) -> requests.Response:
    response = requests.get(
        podcast.rss,
        headers=get_feed_headers(podcast),
        allow_redirects=True,
        timeout=10,
    )

    response.raise_for_status()

    if response.status_code == http.HTTPStatus.NOT_MODIFIED:
        raise NotModified(response=response)

    if (
        response.url != podcast.rss
        and Podcast.objects.filter(rss=response.url).exists()
    ):
        raise DuplicateFeed(response=response)

    return response


def get_frequency(pub_dates: list[datetime]) -> timedelta | None:
    if not pub_dates:
        return None

    prev, *dates = [timezone.now()] + pub_dates

    diffs = []
    for date in dates:
        diffs.append((prev - date).total_seconds())
        prev = date

    seconds = statistics.median(diffs)

    return min(
        max(timedelta(seconds=seconds), MIN_FREQUENCY),
        MAX_FREQUENCY,
    )


def reschedule(frequency: timedelta | None, modifier: float) -> datetime | None:
    if frequency is None:
        return None

    return timezone.now() + timedelta(seconds=frequency.total_seconds() * modifier)


def parse_success(
    podcast: Podcast,
    response: requests.Response,
    feed: rss_parser.Feed,
    items: list[rss_parser.Item],
) -> ParseResult:

    # feed status
    podcast.rss = response.url
    podcast.http_status = response.status_code
    podcast.etag = response.headers.get("ETag", "")
    podcast.modified = date_parser.parse_date(response.headers.get("Last-Modified"))

    now = timezone.now()

    podcast.polled = now
    podcast.queued = None
    podcast.active = True
    podcast.result = Podcast.Result.SUCCESS  # type: ignore
    podcast.exception = ""

    # parsing status
    pub_dates = [item.pub_date for item in items]

    podcast.pub_date = max(pub_dates)
    podcast.frequency = get_frequency(pub_dates) or podcast.frequency
    podcast.frequency_modifier = max(podcast.frequency_modifier / 1.2, 1.0)
    podcast.scheduled = reschedule(podcast.frequency, podcast.frequency_modifier)

    # content

    for field in (
        "cover_url",
        "description",
        "explicit",
        "funding_text",
        "funding_url",
        "language",
        "last_build_date",
        "link",
        "owner",
        "title",
    ):
        setattr(podcast, field, getattr(feed, field))

    # taxonomy
    categories_dct = get_categories_dict()

    categories = [
        categories_dct[category]
        for category in feed.categories
        if category in categories_dct
    ]
    podcast.keywords = " ".join(
        category for category in feed.categories if category not in categories_dct
    )
    podcast.extracted_text = extract_text(podcast, categories, items)

    podcast.categories.set(categories)  # type: ignore

    podcast.save()

    # episodes
    parse_episodes(podcast, items)

    return ParseResult(rss=podcast.rss, success=True, status=response.status_code)


def parse_episodes(
    podcast: Podcast, items: list[rss_parser.Item], batch_size: int = 500
) -> None:
    """Remove any episodes no longer in feed, update any current and
    add new"""

    qs = Episode.objects.filter(podcast=podcast)

    # remove any episodes that may have been deleted on the podcast
    qs.exclude(guid__in=[item.guid for item in items]).delete()

    # determine new/current items
    guids = dict(qs.values_list("guid", "pk"))

    episodes = [
        Episode(pk=guids.get(item.guid), podcast=podcast, **attr.asdict(item))
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
    podcast: Podcast, categories: list[Category], items: list[rss_parser.Item]
) -> str:
    text = " ".join(
        value
        for value in [
            podcast.title,
            podcast.description,
            podcast.keywords,
            podcast.owner,
        ]
        + [c.name for c in categories]
        + [item.title for item in items][:6]
        if value
    )
    return " ".join(text_parser.extract_keywords(podcast.language, text))


def get_feed_headers(podcast: Podcast) -> dict[str, str]:
    headers = {
        "Accept": ACCEPT_HEADER,
        "User-Agent": secrets.choice(USER_AGENTS),
    }

    if podcast.etag:
        headers["If-None-Match"] = quote_etag(podcast.etag)
    if podcast.modified:
        headers["If-Modified-Since"] = http_date(podcast.modified.timestamp())
    return headers


def is_feed_changed(podcast: Podcast, feed: rss_parser.Feed) -> bool:
    return (
        None in (podcast.last_build_date, feed.last_build_date)
        or podcast.last_build_date != feed.last_build_date
    )


@lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")


def parse_failure(
    podcast: Podcast,
    *,
    status: int | None = None,
    active: bool = True,
    result: tuple[str, str] | None = None,
    exception: Exception | None = None,
    tb: str = "",
) -> ParseResult:

    now = timezone.now()
    frequency_modifier = min(podcast.frequency_modifier * 1.2, 1000)

    Podcast.objects.filter(pk=podcast.id).update(
        active=active,
        updated=now,
        polled=now,
        frequency_modifier=frequency_modifier,
        scheduled=reschedule(podcast.frequency, frequency_modifier),
        result=result,
        http_status=status,
        exception=tb,
        queued=None,
    )

    return ParseResult(
        rss=podcast.rss,
        success=False,
        status=status,
        result=result[0] if result else None,
        exception=exception,
    )
