from __future__ import annotations

import http
import secrets
import traceback

from datetime import datetime, timedelta
from functools import lru_cache

import attr
import requests

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.http import http_date, quote_etag
from django_rq import get_queue, job
from rq.worker import Worker

from jcasts.episodes.models import Episode
from jcasts.podcasts import date_parser, rss_parser, scheduler, text_parser
from jcasts.podcasts.models import Category, Podcast

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


@attr.s(kw_only=True)
class ParseResult:
    rss: str | None = attr.ib()
    success: bool = attr.ib(default=False)
    status: int | None = attr.ib(default=None)
    result: str | None = attr.ib(default=None)
    exception: Exception | None = attr.ib(default=None)

    def __bool__(self) -> bool:
        return self.success

    def raise_exception(self) -> None:
        if self.exception:
            raise self.exception


def parse_podcast_feeds(frequency: timedelta | None = None) -> int:
    """
    Parses individual podcast feeds for update.

    If `frequency` is not None will limit number to available workers,
    and will only parse podcasts scheduled for update.

    Returns total number of podcasts parsed.
    """

    qs = (
        Podcast.objects.active()
        .filter(queued=None)
        .distinct()
        .order_by(
            F("scheduled").asc(nulls_first=True),
            F("pub_date").desc(nulls_first=True),
        )
    )

    if frequency:
        num_workers = Worker.count(queue=get_queue("feeds"))
        # rough estimate: takes 2 seconds per update
        limit = num_workers * round(frequency.total_seconds() / 2)
        qs = qs.scheduled()[:limit]

    podcast_ids = list(qs.values_list("pk", flat=True))

    Podcast.objects.filter(pk__in=podcast_ids).update(queued=timezone.now())

    for podcast_id in podcast_ids:
        parse_podcast_feed.delay(podcast_id)

    return len(podcast_ids)


@job("feeds")
@transaction.atomic
def parse_podcast_feed(podcast_id: int) -> ParseResult:

    try:
        podcast = Podcast.objects.active().get(pk=podcast_id)
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
            active=e.response.status_code
            not in (
                http.HTTPStatus.FORBIDDEN,
                http.HTTPStatus.GONE,
                http.HTTPStatus.METHOD_NOT_ALLOWED,
                http.HTTPStatus.NOT_FOUND,
                http.HTTPStatus.UNAUTHORIZED,
            ),
        )

    except requests.RequestException as e:
        return parse_failure(
            podcast,
            exception=e,
            result=Podcast.Result.NETWORK_ERROR,
            active=True,
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

    # parsing result

    podcast.parsed = timezone.now()
    podcast.queued = None
    podcast.active = True
    podcast.result = Podcast.Result.SUCCESS  # type: ignore
    podcast.exception = ""

    # scheduling

    (
        podcast.pub_date,
        podcast.scheduled,
        podcast.schedule_modifier,
    ) = parse_pub_dates(podcast, items)

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

    return ParseResult(
        rss=podcast.rss,
        success=True,
        status=response.status_code if response else None,
    )


def parse_pub_dates(
    podcast: Podcast, items: list[rss_parser.Item]
) -> tuple[datetime | None, datetime | None, float | None]:

    pub_dates = [item.pub_date for item in items if item.pub_date]

    if pub_dates and (latest := max(pub_dates)) != podcast.pub_date:
        return (
            latest,
            *scheduler.schedule(latest, pub_dates),
        )

    return podcast.pub_date, *scheduler.reschedule(
        podcast.pub_date,
        podcast.schedule_modifier,
    )


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
    if active:
        scheduled, modifier = scheduler.reschedule(
            podcast.pub_date, podcast.schedule_modifier
        )
    else:
        scheduled, modifier = None, None

    Podcast.objects.filter(pk=podcast.id).update(
        active=active,
        scheduled=scheduled,
        schedule_modifier=modifier,
        updated=now,
        parsed=now,
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
