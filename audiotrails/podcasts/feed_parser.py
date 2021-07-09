from __future__ import annotations

import http
import secrets
import traceback

from functools import lru_cache

import box
import feedparser
import requests

from django.utils import timezone
from django.utils.http import http_date, quote_etag
from feedparser.http import ACCEPT_HEADER

from audiotrails.episodes.models import Episode
from audiotrails.podcasts.convertors import (
    conv_bool,
    conv_date,
    conv_int,
    conv_list,
    conv_str,
    conv_url,
)
from audiotrails.podcasts.date_parser import parse_date
from audiotrails.podcasts.models import Category, Podcast
from audiotrails.podcasts.text_parser import extract_keywords

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


def parse_feed(podcast: Podcast) -> list[Episode]:

    try:
        response = requests.get(
            podcast.rss,
            headers=get_feed_headers(podcast),
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

    return sync_podcast(podcast, response)


def sync_podcast(podcast: Podcast, response: requests.Response) -> list[Episode]:

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
    podcast.pub_date = max(item.pub_date for item in items)
    podcast.exception = ""

    podcast.title = conv_str(result.feed.title)
    podcast.link = conv_url(result.feed.link)[:500]
    podcast.cover_url = conv_url(result.feed.image.href)
    podcast.language = conv_str(result.feed.language, "en")[:2]

    podcast.description = conv_str(
        result.feed.content,
        result.feed.summary,
        result.feed.description,
        result.feed.subtitle,
    )

    podcast.explicit = conv_bool(result.feed)
    podcast.creators = parse_creators(result.feed)

    keywords, categories = parse_taxonomy(result.feed)

    podcast.keywords = " ".join(keywords)
    podcast.extracted_text = extract_text(podcast, categories, items)
    podcast.categories.set(categories)  # type: ignore

    podcast.save()

    return sync_episodes(podcast, items)


def sync_episodes(podcast: Podcast, items: list[box.Box]) -> list[Episode]:
    episodes = Episode.objects.filter(podcast=podcast)

    # remove any episodes that may have been deleted on the podcast
    episodes.exclude(guid__in=[item.id for item in items]).delete()
    guids = episodes.values_list("guid", flat=True)

    return Episode.objects.bulk_create(
        [make_episode(podcast, item) for item in items if item.id not in guids],
        ignore_conflicts=True,
    )


def make_episode(podcast: Podcast, item: box.Box) -> Episode:
    return Episode(
        podcast=podcast,
        guid=item.id,
        title=item.title,
        pub_date=item.pub_date,
        media_type=item.audio.type[:60],
        explicit=conv_bool(item),
        media_url=conv_url(item.audio.href),
        length=conv_int(item.audio.length),
        link=conv_url(item.link)[:500],
        description=conv_str(item.description, item.summary),
        duration=conv_str(item.itunes_duration)[:30],
        keywords=" ".join(parse_tags(item)),
    )


def parse_tags(item: box.Box) -> list[str]:
    return [tag.term for tag in conv_list(item.tags) if tag.term]


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
            podcast.creators,
        ]
        + [c.name for c in categories]
        + [item.title for item in items][:6]
    )
    return " ".join(extract_keywords(podcast.language, text))


def parse_items(result: box.Box) -> list[box.Box]:
    return [
        item
        for item in [with_pub_date(with_audio(item)) for item in result.entries]
        if is_episode(item)
    ]


def parse_creators(feed: box.Box) -> str:
    return " ".join({author.name for author in conv_list(feed.authors) if author.name})


def with_audio(item: box.Box) -> box.Box:
    for link in conv_list(item.enclosures) + conv_list(item.links):
        if is_audio(link):
            return item + box.Box(audio=link)
    return item


def with_pub_date(item: box.Box) -> box.Box:
    return item + box.Box(pub_date=conv_date(item.published))


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


def get_feed_headers(podcast: Podcast) -> dict[str, str]:
    headers: dict[str, str] = {
        "Accept": ACCEPT_HEADER,
        "User-Agent": secrets.choice(USER_AGENTS),
    }

    if podcast.etag:
        headers["If-None-Match"] = quote_etag(podcast.etag)
    if podcast.modified:
        headers["If-Modified-Since"] = http_date(podcast.modified.timestamp())
    return headers


def resolve_podcast_rss(
    podcast: Podcast, response: requests.Response
) -> tuple[str, bool]:

    if (
        response.status_code
        in (
            http.HTTPStatus.MOVED_PERMANENTLY,
            http.HTTPStatus.PERMANENT_REDIRECT,
        )
        and response.url != podcast.rss
    ):
        return response.url, True
    return response.url, False


def handle_empty_result(podcast: Podcast, **fields) -> list[Episode]:
    if fields:
        for k, v in fields.items():
            setattr(podcast, k, v)
        podcast.save(update_fields=fields.keys())
    return []
