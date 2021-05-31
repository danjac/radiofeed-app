from __future__ import annotations

import functools
import http

from functools import lru_cache
from typing import Any, Callable

import box
import feedparser

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone
from django.utils.encoding import force_str

from audiotrails.episodes.models import Episode
from audiotrails.podcasts.date_parser import parse_date
from audiotrails.podcasts.models import Category, Podcast
from audiotrails.podcasts.text_parser import extract_keywords

MAX_IMAGE_SIZE = 1000


@lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")


def parse_feed(podcast: Podcast) -> list[Episode]:

    result = box.Box(
        feedparser.parse(
            podcast.rss,
            etag=podcast.etag,
            modified=podcast.last_updated,
        ),
        default_box=True,
    )

    if result.status == http.HTTPStatus.GONE:
        # HTTP gone: podcast is dead
        podcast.active = False
        podcast.save()
        return []

    if (
        result.status == http.HTTPStatus.PERMANENT_REDIRECT
        and result.href != podcast.rss
    ):
        # permanent redirect: update URL for next time
        podcast.rss = result.href

    if not (items := parse_items(result)):
        return []

    sync_podcast(podcast, result, items)
    return sync_episodes(podcast, items)


def sync_podcast(
    podcast: Podcast,
    result: box.Box,
    items: list[box.Box],
) -> None:

    # timestamps
    podcast.last_updated = timezone.now()
    podcast.pub_date = max(item.pub_date for item in items)
    podcast.etag = conv_str(result.etag)

    # description
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

    podcast.explicit = parse_explicit(result.feed)
    podcast.creators = parse_creators(result.feed)
    parse_taxonomy(podcast, result.feed, items)

    podcast.save()


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
        media_url=item.audio.href,
        media_type=item.audio.type[:60],
        explicit=parse_explicit(item),
        length=conv_int(item.audio.length),
        link=conv_url(item.link)[:500],
        description=conv_str(item.description, item.summary),
        duration=conv_str(item.itunes_duration)[:30],
        keywords=" ".join(parse_tags(item)),
    )


def parse_tags(item: box.Box) -> list[str]:
    return [tag.term for tag in conv_list(item.tags) if tag.term]


def parse_explicit(item: box.Box) -> bool:
    return bool(item.itunes_explicit)


def parse_taxonomy(podcast: Podcast, feed: box.Box, items: list[box.Box]) -> None:
    """Extract keywords from text content for recommender
    and map to categories"""
    categories_dct = get_categories_dict()
    tags = parse_tags(feed)

    categories = [categories_dct[name] for name in tags if name in categories_dct]

    podcast.keywords = " ".join(name for name in tags if name not in categories_dct)
    podcast.extracted_text = extract_text(podcast, categories, items)
    podcast.categories.set(categories)  # type: ignore


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
    return item + box.Box(pub_date=parse_date(item.published))


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


def conv(
    *values: Any, convert: Callable, default=None, validator: Callable | None = None
) -> Any:
    """Returns first non-falsy value, converting the item. Otherwise returns default value"""
    for value in values:
        if converted := _conv(value, convert, validator):
            return converted
    return default() if callable(default) else default


def _conv(value: Any, convert: Callable, validator: Callable | None = None) -> Any:
    try:
        if value and (converted := convert(value)):
            if validator:
                validator(converted)
            return converted
    except (ValidationError, TypeError, ValueError):
        pass

    return None


conv_str = functools.partial(conv, convert=force_str, default="")
conv_int = functools.partial(conv, convert=int, default=None)
conv_list = functools.partial(conv, convert=list, default=list)

conv_url = functools.partial(
    conv,
    convert=force_str,
    default="",
    validator=URLValidator(schemes=["http", "https"]),
)
