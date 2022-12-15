from __future__ import annotations

import hashlib
import http

from typing import Iterator

import attrs
import httpx
import user_agent

from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.http import http_date, quote_etag

from radiofeed.common import batcher, tokenizer
from radiofeed.episodes.models import Episode
from radiofeed.feedparser import rss_parser, scheduler
from radiofeed.feedparser.date_parser import parse_date
from radiofeed.feedparser.models import Feed, Item
from radiofeed.podcasts.models import Category, Podcast

_ACCEPT_HEADER = (
    "application/atom+xml,"
    "application/rdf+xml,"
    "application/rss+xml,"
    "application/x-netcdf,"
    "application/xml;q=0.9,"
    "text/xml;q=0.2,"
    "*/*;q=0.1"
)


class NotModified(ValueError):
    """RSS feed has not been modified since last update."""


class Duplicate(ValueError):
    """Another identical podcast exists in the database."""


class Inaccessible(ValueError):
    """Content is no longer accesssible."""


def get_client() -> httpx.Client:
    """Returns HTTP client with."""
    return httpx.Client(
        headers={
            "user-agent": user_agent.generate_user_agent(),
            "accept": _ACCEPT_HEADER,
        },
        follow_redirects=True,
        timeout=10,
    )


def parse_feed(podcast: Podcast, client: httpx.Client) -> bool:
    """Parses podcast RSS feed."""
    return FeedParser(podcast).parse(client)


def make_content_hash(content: bytes) -> str:
    """Hashes RSS content."""
    return hashlib.sha256(content).hexdigest()


class FeedParser:
    """Updates a Podcast instance with its RSS or Atom feed source."""

    _max_retries: int = 3

    _feed_attrs = attrs.fields(Feed)
    _item_attrs = attrs.fields(Item)

    def __init__(self, podcast: Podcast):
        self._podcast = podcast

    @transaction.atomic
    def parse(self, client: httpx.Client) -> bool:
        """Updates Podcast instance with RSS or Atom feed source.

        Podcast details are updated and episodes created, updated or deleted accordingly.

        If a podcast is discontinued (e.g. there is a duplicate feed in the database, or the feed is marked as complete) then the podcast is set inactive.
        """
        try:
            return self._handle_success(*self._parse_rss(client))

        except Exception as e:
            return self._handle_exception(e)

    def _parse_rss(self, client: httpx.Client) -> tuple[httpx.Response, Feed, str]:
        response = client.get(self._podcast.rss, headers=self._get_feed_headers())

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (
                http.HTTPStatus.FORBIDDEN,
                http.HTTPStatus.NOT_FOUND,
                http.HTTPStatus.GONE,
                http.HTTPStatus.UNAUTHORIZED,
            ):
                raise Inaccessible()

            if e.response.status_code == http.HTTPStatus.NOT_MODIFIED:
                raise NotModified()

            raise

        # Check if not modified: feed should return a 304 if no new updates,
        # but not in all cases, so we should also check the content body.
        content_hash = make_content_hash(response.content)

        if content_hash == self._podcast.content_hash:
            raise NotModified()

        # Check if there is another active feed with the same URL/content
        if (
            Podcast.objects.exclude(pk=self._podcast.id).filter(
                Q(content_hash=content_hash) | Q(rss=response.url)
            )
        ).exists():
            raise Duplicate()

        return response, rss_parser.parse_rss(response.content), content_hash

    def _get_feed_headers(self) -> dict:
        headers = {}
        if self._podcast.etag:
            headers["If-None-Match"] = quote_etag(self._podcast.etag)
        if self._podcast.modified:
            headers["If-Modified-Since"] = http_date(self._podcast.modified.timestamp())
        return headers

    def _handle_success(
        self,
        response: httpx.Response,
        feed: Feed,
        content_hash: str,
    ) -> bool:

        active = False if feed.complete else True

        categories, keywords = self._extract_categories(feed)

        self._podcast_update(
            active=active,
            num_retries=0,
            content_hash=content_hash,
            keywords=keywords,
            rss=response.url,
            etag=response.headers.get("ETag", ""),
            modified=parse_date(response.headers.get("Last-Modified")),
            extracted_text=self._extract_text(feed),
            frequency=scheduler.schedule(feed),
            **attrs.asdict(
                feed,
                filter=attrs.filters.exclude(  # type: ignore
                    self._feed_attrs.categories,
                    self._feed_attrs.complete,
                    self._feed_attrs.items,
                ),
            ),
        )

        self._podcast.categories.set(categories)
        self._episode_updates(feed)

        return True

    def _handle_exception(self, exc: Exception) -> bool:

        num_retries: int = self._podcast.num_retries
        active: bool = True

        match exc:

            case Inaccessible() | Duplicate():
                active = False

            case NotModified():
                num_retries = 0

            case rss_parser.RssParserError() | httpx.HTTPError():
                num_retries += 1

            case _:
                raise

        self._podcast_update(
            active=active and num_retries < self._max_retries,
            num_retries=num_retries,
            frequency=scheduler.reschedule(
                self._podcast.pub_date,
                self._podcast.frequency,
            ),
        )

        return False

    def _podcast_update(self, **fields) -> None:
        now = timezone.now()

        Podcast.objects.filter(pk=self._podcast.id).update(
            updated=now,
            parsed=now,
            **fields,
        )

    def _extract_categories(self, feed: Feed) -> tuple[list[Category], str]:
        category_names = {c.casefold() for c in feed.categories}

        categories = Category.objects.annotate(lowercase_name=Lower("name")).filter(
            lowercase_name__in=category_names
        )

        return categories, " ".join(
            category_names - {c.lowercase_name for c in categories}
        )

    def _extract_text(self, feed: Feed) -> str:
        text = " ".join(
            value
            for value in [
                feed.title,
                feed.description,
                feed.owner,
            ]
            + feed.categories
            + [item.title for item in feed.items][:6]
            if value
        )
        return " ".join(tokenizer.tokenize(self._podcast.language, text))

    def _episode_updates(self, feed: Feed) -> None:
        qs = Episode.objects.filter(podcast=self._podcast)

        # remove any episodes that may have been deleted on the podcast
        qs.exclude(guid__in={item.guid for item in feed.items}).delete()

        # determine new/current items based on presence of guid

        guids = dict(qs.values_list("guid", "pk"))

        # update existing content

        for batch in batcher.batcher(self._episodes_for_update(feed, guids), 1000):
            Episode.fast_update_objects.copy_update(
                batch,
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
            )

        # add new episodes

        for batch in batcher.batcher(self._episodes_for_insert(feed, guids), 100):
            Episode.objects.bulk_create(batch, ignore_conflicts=True)

    def _episodes_for_insert(
        self, feed: Feed, guids: dict[str, int]
    ) -> Iterator[Episode]:
        return (
            self._make_episode(item) for item in feed.items if item.guid not in guids
        )

    def _episodes_for_update(
        self, feed: Feed, guids: dict[str, int]
    ) -> Iterator[Episode]:

        episode_ids = set()

        for item in (item for item in feed.items if item.guid in guids):
            if (episode_id := guids[item.guid]) not in episode_ids:
                yield self._make_episode(item, episode_id)
                episode_ids.add(episode_id)

    def _make_episode(self, item: Item, episode_id: int | None = None) -> Episode:
        return Episode(
            pk=episode_id,
            podcast=self._podcast,
            **attrs.asdict(
                item,
                filter=attrs.filters.exclude(  # type: ignore
                    self._item_attrs.categories,
                ),
            ),
        )
