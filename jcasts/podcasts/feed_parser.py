from __future__ import annotations

import http
import itertools
import secrets
import traceback

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Optional

import feedparser
import requests

from django.utils import timezone
from django.utils.http import http_date, quote_etag
from django_rq import job
from feedparser.http import ACCEPT_HEADER
from pydantic import BaseModel, HttpUrl, ValidationError, root_validator, validator

from jcasts.episodes.models import Episode
from jcasts.podcasts.date_parser import parse_date
from jcasts.podcasts.models import Category, Podcast
from jcasts.podcasts.scheduler import schedule
from jcasts.podcasts.text_parser import extract_keywords

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]


class ContentItem(BaseModel):
    value: str = ""
    type: str = ""


class Link(BaseModel):
    href: HttpUrl
    length: Optional[int] = None
    type: str = ""
    rel: str = ""

    def is_audio(self) -> bool:
        return self.type.startswith("audio") and self.rel == "enclosure"


class Tag(BaseModel):
    term: str


class Author(BaseModel):
    name: str


class Image(BaseModel):
    href: HttpUrl


class Item(BaseModel):

    id: str
    title: str

    published: datetime
    audio: Link

    link: str = ""
    image: Optional[Image] = None

    itunes_explicit: bool = False
    itunes_season: Optional[int] = None
    itunes_episode: Optional[int] = None
    itunes_episodetype: str = "full"
    itunes_duration: str = ""

    description: str = ""
    summary: str = ""

    content: list[ContentItem] = []
    enclosures: list[Link] = []
    links: list[Link] = []
    tags: list[Tag] = []

    @validator("published", pre=True)
    def get_published(cls, value: str | None) -> datetime | None:
        pub_date = parse_date(value)
        if pub_date and pub_date < timezone.now():
            return pub_date
        raise ValueError("no pub date")

    @validator("itunes_explicit", pre=True)
    def get_explicit(cls, value: str | bool | None) -> bool:
        return is_explicit(value)

    @root_validator(pre=True)
    def get_audio(cls, values: dict) -> dict:
        for value in itertools.chain(
            *[values.get(field, []) for field in ("links", "enclosures")]
        ):
            try:

                if not isinstance(value, Link):
                    value = Link(**value)

                if value.is_audio():
                    return {**values, "audio": value}

            except ValidationError:
                pass

        raise ValueError("audio missing")

    @root_validator
    def get_description_from_content(cls, values: dict) -> dict:
        content_items = values.get("content", [])
        for content_type in ("text/html", "text/plain"):
            for item in content_items:
                if item.value and item.type == content_type:
                    return {**values, "description": item.value}
        return values


class Feed(BaseModel):

    title: str
    link: str = ""

    language: str = "en"

    image: Optional[Image] = None

    author: str = ""
    publisher_detail: Optional[Author] = None

    summary: str = ""
    description: str = ""
    subtitle: str = ""

    itunes_explicit: bool = False

    tags: list[Tag] = []

    @validator("itunes_explicit", pre=True)
    def get_explicit(cls, value: str | bool | None) -> bool:
        return is_explicit(value)

    @validator("language")
    def get_language(cls, value: str) -> str:
        return value[:2]


class Result(BaseModel):
    feed: Feed
    entries: list[Item]

    @validator("entries", pre=True)
    def get_items(cls, value: list) -> list:
        items = []
        for item in value:
            try:
                Item(**item)
            except ValidationError:
                pass
            else:
                items.append(item)
        if not items:
            raise ValueError("feed must have at least 1 item")
        return items


@dataclass
class ParseResult:
    rss: str
    status: int | None = None
    success: bool = False
    exception: Exception | None = None

    def __bool__(self) -> bool:
        return self.success

    def raise_exception(self) -> None:
        if self.exception:
            raise self.exception

    def as_dict(self):

        data = {
            "rss": self.rss,
            "success": self.success,
            "status": self.status,
        }

        try:
            self.raise_exception()
        except Exception:
            data["exception"] = traceback.format_exc()

        return data


@lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")


def parse_frequent_feeds(
    *, force_update: bool = False, limit: int | None = None
) -> int:
    counter = 0
    qs = (
        Podcast.objects.frequent()
        .order_by("scheduled", "-pub_date")
        .values_list("rss", flat=True)
    )

    if not force_update:
        qs = qs.filter(
            scheduled__isnull=False,
            scheduled__lte=timezone.now(),
        )

    if limit:
        qs = qs[:limit]

    for counter, rss in enumerate(qs.iterator(), 1):
        parse_feed.delay(rss, force_update=force_update)

    return counter


def parse_sporadic_feeds(
    *, force_update: bool = False, limit: int | None = None
) -> int:
    counter = 0

    now = timezone.now()

    qs = (
        Podcast.objects.sporadic()
        .filter(
            pub_date__iso_week_day=now.isoweekday(),
        )
        .exclude(
            updated__day=now.day,
            updated__month=now.month,
            updated__year=now.year,
        )
        .order_by("-pub_date")
        .values_list("rss", flat=True)
    )
    if limit:
        qs = qs[:limit]

    for counter, rss in enumerate(qs.iterator(), 1):
        parse_feed.delay(rss, force_update=force_update)

    return counter


@job("feeds")
def parse_feed(rss: str, *, force_update: bool = False) -> ParseResult:
    try:

        podcast = Podcast.objects.get(rss=rss, active=True)
    except Podcast.DoesNotExist as e:
        return ParseResult(rss, None, False, exception=e)

    try:
        response = requests.get(
            podcast.rss,
            headers=get_feed_headers(podcast, force_update),
            allow_redirects=True,
            timeout=10,
        )

        response.raise_for_status()
    except requests.HTTPError:
        # dead feed, don't request again
        return parse_failure(podcast, status=response.status_code, active=False)

    except requests.RequestException as e:
        # temp issue, maybe network error, log & try again later
        return parse_failure(
            podcast, status=e.response.status_code if e.response else None, exception=e
        )

    if response.status_code == http.HTTPStatus.NOT_MODIFIED:
        # no change, ignore
        return parse_failure(podcast, status=response.status_code)

    rss, is_changed = resolve_podcast_rss(podcast, response)

    if is_changed and (
        other := Podcast.objects.filter(rss=rss).exclude(pk=podcast.pk).first()
    ):
        # permanent redirect to URL already taken by another podcast
        return parse_failure(
            podcast, status=response.status_code, redirect_to=other, active=False
        )

    try:
        result = Result.parse_obj(feedparser.parse(response.content))

    except ValidationError as e:
        return parse_failure(podcast, status=response.status_code, exception=e)

    return parse_success(podcast, response, result.feed, result.entries)


def parse_success(
    podcast: Podcast,
    response: requests.Response,
    feed: Feed,
    items: list[Item],
) -> ParseResult:

    podcast.rss = response.url
    podcast.etag = response.headers.get("ETag", "")
    podcast.modified = parse_date(response.headers.get("Last-Modified"))
    podcast.status = response.status_code

    podcast.num_episodes = len(items)

    pub_dates = [item.published for item in items]
    podcast.pub_date = max(pub_dates)
    podcast.scheduled = schedule(podcast, pub_dates)

    podcast.title = feed.title
    podcast.language = feed.language

    podcast.link = feed.link
    podcast.cover_url = feed.image.href if feed.image else None

    podcast.description = feed.summary or feed.description or feed.subtitle

    podcast.owner = feed.publisher_detail.name if feed.publisher_detail else feed.author
    podcast.explicit = feed.itunes_explicit

    categories_dct = get_categories_dict()

    tags = [tag.term for tag in feed.tags if tag.term]
    categories = [categories_dct[tag] for tag in tags if tag in categories_dct]

    podcast.keywords = " ".join(tag for tag in tags if tag not in categories_dct)
    podcast.extracted_text = extract_text(podcast, categories, items)

    podcast.categories.set(categories)  # type: ignore

    parse_episodes(podcast, items)

    result = ParseResult(podcast.rss, response.status_code, True)
    podcast.result = result.as_dict()
    podcast.save()

    return result


def parse_episodes(podcast: Podcast, items: list[Item], batch_size: int = 500) -> None:
    """Remove any episodes no longer in feed, update any current and
    add new"""

    qs = Episode.objects.filter(podcast=podcast)

    # remove any episodes that may have been deleted on the podcast
    qs.exclude(guid__in=[item.id for item in items]).delete()

    # determine new/current items
    guids = dict(qs.values_list("guid", "pk"))

    episodes = [make_episode(podcast, item, guids.get(item.id, None)) for item in items]

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
            "link",
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


def make_episode(podcast: Podcast, item: Item, pk: int | None = None) -> Episode:
    return Episode(
        pk=pk,
        podcast=podcast,
        guid=item.id,
        pub_date=item.published,
        title=item.title,
        link=item.link,
        description=item.description or item.summary,
        explicit=item.itunes_explicit,
        season=item.itunes_season,
        episode=item.itunes_episode,
        episode_type=item.itunes_episodetype,
        cover_url=item.image.href if item.image else None,
        media_url=item.audio.href,
        length=item.audio.length,
        media_type=item.audio.type,
        duration=item.itunes_duration,
        keywords=" ".join([tag.term for tag in item.tags if tag.term]),
    )


def extract_text(
    podcast: Podcast,
    categories: list[Category],
    items: list[Item],
) -> str:
    text = " ".join(
        [
            podcast.title,
            podcast.description,
            podcast.keywords,
            podcast.owner,
        ]
        + [c.name for c in categories]
        + [item.title for item in items][:6]
    )
    return " ".join(extract_keywords(podcast.language, text))


def is_explicit(value: str | bool | None):
    return value not in (False, None, "no", "none")


def get_feed_headers(podcast: Podcast, force_update: bool = False) -> dict[str, str]:
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


def resolve_podcast_rss(
    podcast: Podcast, response: requests.Response
) -> tuple[str, bool]:

    return response.url, (
        response.status_code
        in (
            http.HTTPStatus.MOVED_PERMANENTLY,
            http.HTTPStatus.PERMANENT_REDIRECT,
        )
        or response.url != podcast.rss
    )


def parse_failure(
    podcast: Podcast,
    *,
    status: int | None,
    exception: Exception | None = None,
    active: bool = True,
    **fields,
) -> ParseResult:

    result = ParseResult(podcast.rss, status, False, exception)

    Podcast.objects.filter(pk=podcast.id).update(
        result=result.as_dict(),
        scheduled=schedule(podcast) if active else None,
        updated=timezone.now(),
        active=active,
        **fields,
    )

    return result
