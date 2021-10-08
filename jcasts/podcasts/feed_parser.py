import http
import multiprocessing
import secrets
import traceback

from datetime import timedelta
from functools import lru_cache
from typing import Optional

import attr
import requests

from django.db import transaction
from django.utils import timezone
from django.utils.http import http_date, quote_etag
from django_rq import get_queue, job

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

MIN_SCHEDULED_DELTA = timedelta(hours=1)


class NotModified(requests.RequestException):
    ...


class DuplicateFeed(requests.RequestException):
    ...


def clear_podcast_feed_queue():
    get_queue("feeds").empty()
    Podcast.objects.filter(queued__isnull=False).update(queued=None)


def reschedule_podcast_feeds():

    podcasts = Podcast.objects.filter(active=True, pub_date__isnull=False)
    for_update = []

    for podcast in podcasts:
        podcast.scheduled = reschedule(podcast)
        for_update.append(podcast)

    Podcast.objects.bulk_update(for_update, fields=["scheduled"])


def schedule_podcast_feeds():
    now = timezone.now()

    # rough estimate: 1800 feeds/hour/CPU
    limit = multiprocessing.cpu_count() * 1800

    podcasts = Podcast.objects.filter(
        active=True,
        queued__isnull=True,
        scheduled__isnull=False,
        scheduled__lt=now,
    ).order_by("scheduled", "-pub_date")[:limit]

    for_update = []

    for podcast in podcasts.iterator():
        parse_podcast_feed.delay(podcast.rss)
        podcast.queued = now
        for_update.append(podcast)

    Podcast.objects.bulk_update(for_update, fields=["queued"])


@attr.s(kw_only=True)
class ParseResult:
    rss: str = attr.ib()
    success: bool = attr.ib(default=False)
    status: Optional[http.HTTPStatus] = attr.ib(default=None)
    exception: Optional[Exception] = attr.ib(default=None)

    def __bool__(self):
        return self.success

    def raise_exception(self):
        if self.exception:
            raise self.exception


@job("feeds")
@transaction.atomic
def parse_podcast_feed(rss):

    try:
        podcast = Podcast.objects.get(rss=rss, active=True)
        response = get_feed_response(podcast)

        return parse_success(podcast, response, *rss_parser.parse_rss(response.content))

    except Podcast.DoesNotExist as e:
        return ParseResult(rss=rss, success=False, exception=e)

    except NotModified as e:
        return parse_failure(podcast, status=e.response.status_code)

    except requests.RequestException as e:
        return parse_failure(
            podcast,
            status=e.response.status_code if e.response else None,
            active=False,
            exception=e,
            tb=traceback.format_exc(),
        )

    except rss_parser.RssParserError as e:
        return parse_failure(
            podcast,
            status=response.status_code,
            active=False,
            exception=e,
            tb=traceback.format_exc(),
        )


def get_feed_response(podcast):
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


def parse_success(podcast, response, feed, items):

    # feed status
    podcast.rss = response.url
    podcast.http_status = response.status_code
    podcast.etag = response.headers.get("ETag", "")
    podcast.modified = date_parser.parse_date(response.headers.get("Last-Modified"))

    # parsing status
    pub_dates = [item.pub_date for item in items]

    now = timezone.now()

    podcast.pub_date = max(pub_dates)
    podcast.parsed = now
    podcast.succeeded = now
    podcast.queued = None
    podcast.scheduled = reschedule(podcast)
    podcast.active = True
    podcast.exception = ""

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


def parse_episodes(podcast, items, batch_size=500):
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


def extract_text(podcast, categories, items):
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


def get_feed_headers(podcast):
    headers = {
        "Accept": ACCEPT_HEADER,
        "User-Agent": secrets.choice(USER_AGENTS),
    }

    if podcast.etag:
        headers["If-None-Match"] = quote_etag(podcast.etag)
    if podcast.modified:
        headers["If-Modified-Since"] = http_date(podcast.modified.timestamp())
    return headers


@lru_cache
def get_categories_dict():
    return Category.objects.in_bulk(field_name="name")


def reschedule(podcast):

    now = timezone.now()

    # add 5% since last time to current time
    # e.g. 7 days - try again in about 8 hours
    if podcast.succeeded:
        diff = max(
            timedelta(seconds=(now - podcast.succeeded).total_seconds() * 0.05),
            MIN_SCHEDULED_DELTA,
        )
    else:
        diff = MIN_SCHEDULED_DELTA

    seconds = int(diff.total_seconds() / 2)

    diff = diff + timedelta(seconds=secrets.choice(range(-seconds, seconds)))

    scheduled = now + diff

    return scheduled


def parse_failure(
    podcast,
    *,
    status=None,
    active=True,
    exception=None,
    tb="",
    **fields,
):

    now = timezone.now()

    Podcast.objects.filter(pk=podcast.id).update(
        active=active,
        updated=now,
        parsed=now,
        queued=None,
        scheduled=reschedule(podcast) if active else None,
        http_status=status,
        exception=tb,
        **fields,
    )

    return ParseResult(
        rss=podcast.rss,
        success=False,
        status=status,
        exception=exception,
    )
