from __future__ import annotations

import http
import secrets
import traceback

from datetime import timedelta
from functools import lru_cache

import attr
import requests

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.http import http_date, quote_etag
from django_rq import get_queue

from jcasts.episodes.models import Episode
from jcasts.podcasts import date_parser, rss_parser, text_parser
from jcasts.podcasts.models import Category, Podcast
from jcasts.websub import subscriber
from jcasts.websub.models import Subscription

ACCEPT_HEADER = "application/atom+xml,application/rdf+xml,application/rss+xml,application/x-netcdf,application/xml;q=0.9,text/xml;q=0.2,*/*;q=0.1"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]

PARSE_ERROR_LIMIT = 12  # max errors before podcast is "dead"


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


def parse_podcast_feeds(
    *,
    queue: str = "feeds",
    limit: int = 200,
    followed: bool = False,
    promoted: bool = False,
    after: timedelta | None = None,
    before: timedelta | None = None,
) -> None:
    now = timezone.now()

    q = Q()

    if after:
        q = q | Q(pub_date__gte=now - after) | Q(pub_date__isnull=True)

    if before:
        q = q | Q(pub_date__lt=now - before)

    enqueue_many(
        Podcast.objects.with_followed()
        .with_subscribed()
        .filter(
            q,
            active=True,
            subscribed=False,
            queued__isnull=True,
            followed=followed,
            promoted=promoted,
        )
        .order_by(
            F("parsed").asc(nulls_first=True),
            F("pub_date").desc(nulls_first=True),
        )
        .values_list("pk", flat=True)[:limit],
        queue=queue,
    )


def enqueue_many(podcast_ids: list[int], queue: str = "feeds") -> None:

    if not podcast_ids:
        return

    now = timezone.now()

    Podcast.objects.filter(pk__in=podcast_ids).update(queued=now, updated=now)

    job_queue = get_queue(queue)

    for podcast_id in podcast_ids:
        job_queue.enqueue(parse_podcast_feed, podcast_id)


def enqueue(podcast_id: int, queue: str = "feeds", url: str = "") -> None:

    now = timezone.now()

    Podcast.objects.filter(pk=podcast_id).update(queued=now, updated=now)
    get_queue(queue).enqueue(parse_podcast_feed, podcast_id, url)


@transaction.atomic
def parse_podcast_feed(podcast_id: int, url: str = "") -> ParseResult:

    try:
        podcast = Podcast.objects.filter(active=True).get(pk=podcast_id)
        response, feed, items = parse_content(podcast, url)
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
            result=Podcast.Result.DUPLICATE_FEED,
            status=e.response.status_code,
            active=False,
        )

    except requests.HTTPError as e:

        dead = e.response.status_code == http.HTTPStatus.GONE

        return parse_failure(
            podcast,
            result=Podcast.Result.HTTP_ERROR,
            status=e.response.status_code,
            active=not dead,
            error=not dead,
        )

    except requests.RequestException as e:
        return parse_failure(
            podcast,
            exception=e,
            result=Podcast.Result.NETWORK_ERROR,
            tb=traceback.format_exc(),
            error=True,
        )

    except rss_parser.RssParserError as e:
        return parse_failure(
            podcast,
            result=Podcast.Result.INVALID_RSS,
            exception=e,
            tb=traceback.format_exc(),
            error=True,
        )


def parse_content(
    podcast: Podcast,
    url: str = "",
) -> tuple[requests.Response, rss_parser.Feed, list[rss_parser.Item]]:

    response = get_feed_response(podcast, url)
    feed, items = rss_parser.parse_rss(response.content)
    return response, feed, items


def get_feed_response(podcast: Podcast, url: str = "") -> requests.Response:
    response = requests.get(
        url or podcast.rss,
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
    podcast.result = Podcast.Result.SUCCESS  # type: ignore
    podcast.exception = ""

    podcast.active = not feed.complete
    podcast.errors = 0

    podcast.pub_date = max([item.pub_date for item in items if item.pub_date])

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

    # websub
    parse_websub(podcast, response, feed)

    # episodes
    parse_episodes(podcast, items)

    return ParseResult(
        rss=podcast.rss,
        success=True,
        status=response.status_code,
    )


def parse_websub(
    podcast: Podcast, response: requests.Response, feed: rss_parser.Feed
) -> None:

    # https://w3c.github.io/websub

    # default: hub/topic in Atom links
    hub = feed.websub_hub
    topic = feed.websub_topic

    # also check Link headers
    if "self" in response.links and "hub" in response.links:
        hub = response.links["hub"]["url"]
        topic = response.links["self"]["url"]

    if hub and topic:

        subscription, created = Subscription.objects.get_or_create(
            podcast=podcast,
            hub=hub,
            topic=topic,
        )

        if created:
            subscriber.subscribe.delay(subscription.id)


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


@lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")


def parse_failure(
    podcast: Podcast,
    *,
    status: int | None = None,
    active: bool = True,
    error: bool = False,
    result: tuple[str, str] | None = None,
    exception: Exception | None = None,
    tb: str = "",
) -> ParseResult:

    errors = podcast.errors + 1 if error else 0
    active = active and errors < PARSE_ERROR_LIMIT

    now = timezone.now()

    Podcast.objects.filter(pk=podcast.id).update(
        parsed=now,
        updated=now,
        active=active,
        result=result,
        http_status=status,
        exception=tb,
        errors=errors,
        queued=None,
    )

    return ParseResult(
        rss=podcast.rss,
        success=False,
        status=status,
        result=result[0] if result else None,
        exception=exception,
    )
