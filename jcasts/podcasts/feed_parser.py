from __future__ import annotations

import http
import secrets
import traceback

from functools import lru_cache
from typing import Generator

import box
import feedparser
import requests

from django.conf import settings
from django.utils import timezone
from django.utils.http import http_date, quote_etag
from django_rq import job
from feedparser.http import ACCEPT_HEADER

from jcasts.episodes.models import Episode
from jcasts.podcasts.coerce import (
    coerce_bool,
    coerce_date,
    coerce_int,
    coerce_list,
    coerce_str,
    coerce_url,
)
from jcasts.podcasts.date_parser import parse_date
from jcasts.podcasts.models import Category, Podcast
from jcasts.podcasts.scheduler import (
    calc_frequency,
    calc_frequency_from_podcast,
    get_next_scheduled,
)
from jcasts.podcasts.text_parser import extract_keywords

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]


@lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")


def parse_frequent_feeds(force_update: bool = False) -> int:
    now = timezone.now()
    counter = 0
    qs = (
        Podcast.objects.filter(
            active=True,
            pub_date__gte=now - settings.RELEVANCY_THRESHOLD,
        )
        .order_by("-scheduled", "-pub_date")
        .values_list("rss", flat=True)
    )

    if not force_update:
        qs = qs.filter(
            scheduled__isnull=False,
            scheduled__lte=now,
        )

    for counter, rss in enumerate(qs.iterator(), 1):
        parse_feed.delay(rss, force_update=force_update)

    return counter


def parse_sporadic_feeds() -> int:
    "Should run daily. Matches older feeds with same weekday in last pub date"
    now = timezone.now()
    counter = 0
    for counter, rss in enumerate(
        Podcast.objects.filter(
            active=True,
            pub_date__lt=now - settings.RELEVANCY_THRESHOLD,
            pub_date__iso_week_day=now.isoweekday(),
        )
        .order_by("-pub_date")
        .values_list("rss", flat=True)
        .iterator(),
        1,
    ):
        parse_feed.delay(rss)

    return counter


@job("feeds")
def parse_feed(rss: str, *, force_update: bool = False) -> bool:
    try:

        podcast = Podcast.objects.get(rss=rss, active=True)
    except Podcast.DoesNotExist:
        return False

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
        return handle_empty_result(
            podcast, error_status=response.status_code, active=False
        )

    except requests.RequestException:
        # temp issue, maybe network error, log & try again later
        return handle_empty_result(podcast, exception=traceback.format_exc())

    if response.status_code == http.HTTPStatus.NOT_MODIFIED:
        # no change, ignore
        return handle_empty_result(podcast)

    return parse_podcast(podcast, response)


def parse_podcast(podcast: Podcast, response: requests.Response) -> bool:

    rss, is_changed = resolve_podcast_rss(podcast, response)

    if is_changed and (
        other := Podcast.objects.filter(rss=rss).exclude(pk=podcast.pk).first()
    ):
        # permanent redirect to URL already taken by another podcast
        return handle_empty_result(podcast, redirect_to=other, active=False)

    result = box.Box(feedparser.parse(response.content), default_box=True)

    # check if any items
    if not (items := parse_items(result)):
        return handle_empty_result(podcast, rss=rss)

    podcast.rss = rss
    podcast.etag = response.headers.get("ETag", "")
    podcast.modified = parse_date(response.headers.get("Last-Modified"))
    podcast.exception = ""

    podcast.num_episodes = len(items)

    pub_dates = [item.pub_date for item in items]

    podcast.pub_date = max(pub_dates)
    podcast.frequency = calc_frequency(pub_dates)

    podcast.scheduled = get_next_scheduled(
        frequency=podcast.frequency,
        pub_date=podcast.pub_date,
    )

    podcast.title = coerce_str(result.feed.title)
    podcast.link = coerce_url(result.feed.link)
    podcast.cover_url = coerce_url(result.feed.image.href)

    podcast.language = coerce_str(result.feed.language, "en", limit=2)

    podcast.description = coerce_str(
        result.feed.content,
        result.feed.summary,
        result.feed.description,
        result.feed.subtitle,
    )

    podcast.owner = coerce_str(
        result.feed.publisher_detail.name,
        result.feed.author,
    )

    podcast.explicit = coerce_bool(result.feed.itunes_explicit)

    keywords, categories = parse_taxonomy(result.feed)

    podcast.keywords = " ".join(keywords)
    podcast.extracted_text = extract_text(podcast, categories, items)
    podcast.categories.set(categories)  # type: ignore

    podcast.save()

    parse_episodes(podcast, items)

    return True


def parse_episodes(podcast: Podcast, items: list[box.Box]) -> None:
    """Remove any episodes no longer in feed, update any current and
    add new"""

    qs = Episode.objects.filter(podcast=podcast)

    # remove any episodes that may have been deleted on the podcast
    qs.exclude(guid__in=[item.id for item in items]).delete()

    # determine new/current items
    guid_map = dict(qs.values_list("guid", "pk"))

    episodes = [
        make_episode(podcast, item, guid_map.get(item.id, None)) for item in items
    ]

    guids = guid_map.keys()

    # update existing content

    Episode.objects.bulk_update(
        [episode for episode in episodes if episode.guid in guids],
        fields=[
            "title",
            "description",
            "keywords",
            "cover_url",
            "media_url",
            "media_type",
            "length",
            "link",
            "duration",
            "explicit",
        ],
    )

    # new episodes

    Episode.objects.bulk_create(
        [episode for episode in episodes if episode.guid not in guids],
        ignore_conflicts=True,
    )


def make_episode(podcast: Podcast, item: box.Box, pk: int | None = None) -> Episode:
    return Episode(
        pk=pk,
        podcast=podcast,
        guid=item.id,
        title=item.title,
        pub_date=item.pub_date,
        explicit=coerce_bool(item.itunes_explicit),
        cover_url=coerce_url(item.image.href),
        media_url=coerce_url(item.audio.href),
        length=coerce_int(item.audio.length),
        link=coerce_url(item.link),
        media_type=coerce_str(item.audio.type, limit=60),
        description=coerce_str(item.description, item.summary),
        duration=coerce_str(item.itunes_duration, limit=30),
        keywords=" ".join(parse_tags(item)),
    )


def parse_tags(item: box.Box) -> list[str]:
    return [tag.term for tag in coerce_list(item.tags) if tag.term]


def parse_taxonomy(feed: box.Box) -> tuple[list[str], list[Category]]:
    categories_dct = get_categories_dict()
    tags = parse_tags(feed)
    return (
        [name for name in tags if name not in categories_dct],
        [categories_dct[name] for name in tags if name in categories_dct],
    )


def extract_text(
    podcast: Podcast,
    categories: list[Category],
    items: list[box.Box],
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


def parse_items(result: box.Box) -> list[box.Box]:
    return [
        item
        for item in [parse_item(item) for item in result.entries]
        if is_episode(item)
    ]


def parse_item(item: box.Box) -> box.Box:
    return with_description(with_pub_date(with_audio(item)))


def with_audio(item: box.Box) -> box.Box:
    for link in coerce_list(item.enclosures) + coerce_list(item.links):
        if is_audio(link):
            return item + box.Box(audio=link)
    return item


def with_pub_date(item: box.Box) -> box.Box:
    return item + box.Box(pub_date=coerce_date(item.published))


def with_description(item: box.Box) -> box.Box:
    return item + box.Box(
        description=coerce_str(
            *parse_content(item),
            item.description,
            item.summary,
        )
    )


def parse_content(item: box.Box) -> Generator[str, None, None]:
    contents = coerce_list(item.content)
    for content_type in ("text/html", "text/plain"):
        for content in contents:
            if coerce_str(content.type) == content_type:
                yield coerce_str(content.value)


def is_audio(link: box.Box) -> bool:
    return (
        link.type
        and link.type.startswith("audio/")
        and link.href
        and link.rel == "enclosure"
    )


def is_episode(item: box.Box) -> bool:
    return all(
        (
            item.id,
            item.audio,
            item.pub_date and item.pub_date < timezone.now(),
        )
    )


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


def handle_empty_result(podcast: Podcast, active=True, **fields) -> bool:
    frequency = calc_frequency_from_podcast(podcast) if active else None

    Podcast.objects.filter(pk=podcast.id).update(
        active=active,
        frequency=frequency,
        scheduled=get_next_scheduled(pub_date=podcast.pub_date, frequency=frequency),
        updated=timezone.now(),
        **fields,
    )

    return False
