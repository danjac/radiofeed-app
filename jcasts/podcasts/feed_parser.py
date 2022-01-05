from __future__ import annotations

import hashlib
import http

from functools import lru_cache

import attr
import requests

from django.db import transaction
from django.utils import timezone
from django.utils.http import http_date, quote_etag

from jcasts.episodes.models import Episode
from jcasts.podcasts import date_parser, rss_parser, text_parser, user_agent
from jcasts.podcasts.models import Category, Podcast

ACCEPT_HEADER = "application/atom+xml,application/rdf+xml,application/rss+xml,application/x-netcdf,application/xml;q=0.9,text/xml;q=0.2,*/*;q=0.1"

PARSE_ERROR_LIMIT = 3  # max errors before podcast is "dead"


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


@transaction.atomic
def parse_podcast_feed(podcast_id: int) -> ParseResult:

    try:
        podcast = Podcast.objects.filter(active=True).get(pk=podcast_id)
        return parse_hit(podcast, *parse_content(podcast))

    except Podcast.DoesNotExist as e:
        return ParseResult(rss=None, success=False, exception=e)

    except NotModified as e:
        return parse_miss(
            podcast,
            result=Podcast.Result.NOT_MODIFIED,  # type: ignore
            status=e.response.status_code,
        )

    except DuplicateFeed as e:
        return parse_miss(
            podcast,
            result=Podcast.Result.DUPLICATE_FEED,  # type: ignore
            status=e.response.status_code,
            active=False,
        )

    except requests.HTTPError as e:

        if e.response.status_code == http.HTTPStatus.GONE:
            return parse_miss(
                podcast,
                result=Podcast.Result.HTTP_ERROR,  # type: ignore
                status=e.response.status_code,
                active=False,
            )

        return parse_miss(
            podcast,
            result=Podcast.Result.HTTP_ERROR,  # type: ignore
            status=e.response.status_code,
            exception=e,
        )

    except requests.RequestException as e:
        return parse_miss(
            podcast,
            result=Podcast.Result.NETWORK_ERROR,  # type: ignore
            exception=e,
        )

    except rss_parser.RssParserError as e:
        return parse_miss(
            podcast,
            result=Podcast.Result.INVALID_RSS,  # type: ignore
            exception=e,
        )


def parse_content(
    podcast: Podcast,
) -> tuple[requests.Response, str, rss_parser.Feed, list[rss_parser.Item]]:

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

    if (content_hash := make_content_hash(response.content)) == podcast.content_hash:
        raise NotModified(response=response)

    return response, content_hash, *rss_parser.parse_rss(response.content)


def parse_hit(
    podcast: Podcast,
    response: requests.Response,
    content_hash: str,
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
    podcast.feed_queue = None
    podcast.result = Podcast.Result.SUCCESS  # type: ignore
    podcast.content_hash = content_hash
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

    # episodes
    parse_episodes(podcast, items)

    return ParseResult(
        rss=podcast.rss,
        success=True,
        status=response.status_code,
    )


def parse_miss(
    podcast: Podcast,
    *,
    active: bool = True,
    status: int | None = None,
    result: Podcast.Result | None = None,
    exception: Exception | None = None,
) -> ParseResult:

    now = timezone.now()

    errors = podcast.errors + 1 if exception else 0
    active = active and errors < PARSE_ERROR_LIMIT

    Podcast.objects.filter(pk=podcast.id).update(
        active=active,
        result=result,
        http_status=status,
        errors=errors,
        parsed=now,
        updated=now,
        queued=None,
        feed_queue=None,
    )

    return ParseResult(
        rss=podcast.rss,
        success=False,
        status=status,
        exception=exception,
        result=result.value if result else None,
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
        "User-Agent": user_agent.get_user_agent(),
    }

    if podcast.etag:
        headers["If-None-Match"] = quote_etag(podcast.etag)
    if podcast.modified:
        headers["If-Modified-Since"] = http_date(podcast.modified.timestamp())
    return headers


def make_content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")
