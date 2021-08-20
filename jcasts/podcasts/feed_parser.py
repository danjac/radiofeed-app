from __future__ import annotations

import http
import secrets

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Optional

import lxml
import requests

from django.db import transaction
from django.utils import timezone
from django.utils.http import http_date, quote_etag
from django_rq import job
from pydantic import BaseModel, HttpUrl, ValidationError, validator

from jcasts.episodes.models import Episode
from jcasts.podcasts.date_parser import parse_date
from jcasts.podcasts.models import Category, Podcast
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

NAMESPACES = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}


def parse_podcast_feeds(*, force_update: bool = False, limit: int | None = None) -> int:
    counter = 0
    qs = (
        Podcast.objects.filter(active=True)
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


class Item(BaseModel):

    guid: str
    title: str
    link: str = ""

    pub_date: datetime

    cover_url: Optional[HttpUrl]

    media_url: HttpUrl
    media_type: str
    length: Optional[int] = None

    explicit: bool = False

    season: Optional[int] = None
    episode: Optional[int] = None
    episode_type: str = "full"
    duration: str = ""

    description: str = ""
    keywords: str = ""

    @validator("pub_date", pre=True)
    def get_pub_date(cls, value: str | None) -> datetime | None:
        pub_date = parse_date(value)
        if pub_date and pub_date < timezone.now():
            return pub_date
        raise ValueError("not a valid pub date")

    @validator("explicit", pre=True)
    def is_explicit(cls, value: str) -> bool:
        return value.lower() in ("yes", "clean") if value else False

    @validator("keywords", pre=True)
    def get_keywords(cls, value: list) -> str:
        return " ".join(value)

    @validator("media_type")
    def is_audio(cls, value: str) -> str:
        if not (value or "").startswith("audio/"):
            raise ValueError("not a valid audio enclosure")
        return value


class Feed(BaseModel):

    title: str
    link: str = ""

    language: str = "en"
    cover_url: Optional[HttpUrl]

    owner: str = ""
    description: str = ""

    explicit: bool = False

    categories: list[str] = []

    @validator("explicit", pre=True)
    def is_explicit(cls, value: str) -> bool:
        return value.lower() in ("yes", "clean") if value else False

    @validator("language")
    def get_language(cls, value: str) -> str:
        return value[:2]


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


@job("feeds")
@transaction.atomic
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

    if (
        response.url != podcast.rss
        and Podcast.objects.filter(rss=response.url).exists()
    ):
        # permanent redirect to URL already taken by another podcast
        return parse_failure(podcast, status=response.status_code, active=False)

    try:
        feed, items = parse_rss(response.content)

    except (lxml.etree.ParseError, ValidationError, ValueError) as e:
        return parse_failure(podcast, status=response.status_code, exception=e)

    return parse_success(podcast, response, feed, items)


def parse_success(
    podcast: Podcast,
    response: requests.Response,
    feed: Feed,
    items: list[Item],
) -> ParseResult:

    # feed status
    podcast.rss = response.url
    podcast.etag = response.headers.get("ETag", "")
    podcast.modified = parse_date(response.headers.get("Last-Modified"))

    # parsing status
    pub_dates = [item.pub_date for item in items]

    podcast.num_episodes = len(items)
    podcast.pub_date = max(pub_dates)
    podcast.scheduled = schedule(podcast, pub_dates)
    podcast.parsed = timezone.now()

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
    print(feed.categories)

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

    return ParseResult(podcast.rss, response.status_code, True)


def parse_episodes(podcast: Podcast, items: list[Item], batch_size: int = 500) -> None:
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


@lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")


def parse_failure(
    podcast: Podcast,
    *,
    status: int | None,
    exception: Exception | None = None,
    active: bool = True,
    **fields,
) -> ParseResult:

    now = timezone.now()

    Podcast.objects.filter(pk=podcast.id).update(
        active=active,
        scheduled=schedule(podcast) if active else None,
        updated=now,
        parsed=now,
        **fields,
    )

    return ParseResult(podcast.rss, status, False, exception)


class Mapping:
    def __init__(self, *paths: str, multiple: bool = False):
        self.paths = paths
        self.multiple = multiple

    def parse(self, element: lxml.etree.Element) -> str | list:
        for path in self.paths:
            if value := element.xpath(path, namespaces=NAMESPACES):
                return value if self.multiple else value[0]
        return [] if self.multiple else ""


ITEM_MAPPINGS = {
    "guid": Mapping("guid/text()"),
    "title": Mapping("title/text()"),
    "link": Mapping("link/text()"),
    "description": Mapping("description/text()"),
    "pub_date": Mapping("pubDate/text()"),
    "media_url": Mapping("enclosure//@url"),
    "media_type": Mapping("enclosure//@type"),
    "length": Mapping("enclosure//@length"),
    "cover_url": Mapping("itunes:image/@href"),
    "duration": Mapping("itunes:duration/text()"),
    "explicit": Mapping("itunes:explicit/text()"),
    "episode": Mapping("itunes:episode/text()"),
    "episode_type": Mapping("itunes:episodetype/text()"),
    "season": Mapping("itunes:season/text()"),
    "keywords": Mapping("category/text()", multiple=True),
}

FEED_MAPPINGS = {
    "title": Mapping("title/text()"),
    "link": Mapping("link/text()"),
    "language": Mapping("language/text()"),
    "description": Mapping("description/text()"),
    "cover_url": Mapping("image/url/text()"),
    "explicit": Mapping("itunes:explicit/text()"),
    "owner": Mapping(
        "itunes:author/text()",
        "itunes:owner/itunes:name/text()",
    ),
    "categories": Mapping("//itunes:category/@text", multiple=True),
}


def parse(element: lxml.etree.Element, mappings: dict[str, Mapping]) -> dict:
    parsed = {}
    for field, mapping in mappings.items():
        parsed[field] = mapping.parse(element)
    return parsed


def parse_rss(content: bytes) -> tuple[Feed, list[Item]]:
    xml = lxml.etree.fromstring(content)
    if (channel := xml.find("channel")) is None:
        raise ValueError("<channel /> not found")

    feed = Feed.parse_obj(parse(channel, FEED_MAPPINGS))

    items = [
        item
        for item in [parse_item(element) for element in channel.iterfind("item")]
        if item
    ]
    if not items:
        raise ValueError("no valid entries found")

    return feed, items


def parse_item(element: lxml.etree.Element) -> Item | None:

    try:
        return Item.parse_obj(parse(element, ITEM_MAPPINGS))
    except ValidationError as e:
        print(e)
        return None
