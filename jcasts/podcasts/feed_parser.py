import http
import secrets
import traceback

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import requests

from django.db import transaction
from django.utils import timezone
from django.utils.http import http_date, quote_etag
from django_rq import job

from jcasts.episodes.models import Episode
from jcasts.podcasts.date_parser import parse_date
from jcasts.podcasts.models import Category, Podcast
from jcasts.podcasts.rss_parser import RssParserError, parse_rss
from jcasts.podcasts.scheduler import schedule
from jcasts.podcasts.text_parser import extract_keywords

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


def parse_podcast_feeds(*, force_update=False, limit=None):
    counter = 0
    qs = Podcast.objects.order_by("scheduled", "-pub_date").values_list(
        "rss", flat=True
    )

    if not force_update:
        qs = qs.filter(
            active=True,
            scheduled__isnull=False,
            scheduled__lte=timezone.now(),
        )

    if limit:
        qs = qs[:limit]

    for counter, rss in enumerate(qs.iterator(), 1):
        parse_feed.delay(rss, force_update=force_update)

    return counter


@dataclass
class ParseResult:
    rss: str
    success: bool = False
    status: Optional[http.HTTPStatus] = None
    exception: Optional[Exception] = None

    def __bool__(self):
        return self.success

    def raise_exception(self):
        if self.exception:
            raise self.exception


@job("feeds")
@transaction.atomic
def parse_feed(rss, *, force_update=False):

    try:
        podcast = get_podcast(rss, force_update)
        response = get_feed_response(podcast, force_update)

        return parse_success(podcast, response, *parse_rss(response.content))

    except Podcast.DoesNotExist as e:
        return ParseResult(rss, success=False, status=None, exception=e)

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

    except RssParserError as e:
        return parse_failure(
            podcast,
            status=response.status_code,
            active=False,
            exception=e,
            tb=traceback.format_exc(),
        )


def get_feed_response(podcast, force_update=False):
    response = requests.get(
        podcast.rss,
        headers=get_feed_headers(podcast, force_update),
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
    podcast.modified = parse_date(response.headers.get("Last-Modified"))

    # parsing status
    pub_dates = [item.pub_date for item in items]

    podcast.num_episodes = len(items)
    podcast.pub_date = max(pub_dates)
    podcast.scheduled = schedule(podcast, pub_dates)
    podcast.parsed = timezone.now()
    podcast.active = True
    podcast.exception = ""

    # content

    values = feed.dict()

    for field in (
        "title",
        "language",
        "link",
        "cover_url",
        "description",
        "owner",
        "explicit",
    ):
        setattr(podcast, field, values[field])

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

    return ParseResult(podcast.rss, success=True, status=response.status_code)


def parse_episodes(podcast, items, batch_size=500):
    """Remove any episodes no longer in feed, update any current and
    add new"""

    qs = Episode.objects.filter(podcast=podcast)

    # remove any episodes that may have been deleted on the podcast
    qs.exclude(guid__in=[item.guid for item in items]).delete()

    # determine new/current items
    guids = dict(qs.values_list("guid", "pk"))

    episodes = [
        Episode(pk=guids.get(item.guid, None), podcast=podcast, **item.dict())
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
    return " ".join(extract_keywords(podcast.language, text))


def get_feed_headers(podcast, force_update=False):
    headers: dict[str, str] = {
        "Accept": ACCEPT_HEADER,
        "User-Agent": secrets.choice(USER_AGENTS),
    }

    # ignore any modified/etag headers
    if force_update:
        return headers

    if podcast.etag:
        headers["If-None-Match"] = quote_etag(podcast.etag)
    if podcast.modified:
        headers["If-Modified-Since"] = http_date(podcast.modified.timestamp())
    return headers


@lru_cache
def get_categories_dict():
    return Category.objects.in_bulk(field_name="name")


def get_podcast(rss, force_update=False):

    qs = Podcast.objects.filter(rss=rss)
    if not force_update:
        qs = qs.filter(active=True)
    return qs.get()


def parse_failure(
    podcast,
    *,
    status,
    active=True,
    exception=None,
    tb: str = "",
    **fields,
):

    now = timezone.now()

    Podcast.objects.filter(pk=podcast.id).update(
        active=active,
        scheduled=schedule(podcast) if active else None,
        updated=now,
        parsed=now,
        http_status=status,
        exception=tb,
        **fields,
    )

    return ParseResult(podcast.rss, success=False, status=status, exception=exception)
