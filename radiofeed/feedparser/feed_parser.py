import functools
import hashlib
import itertools
from collections.abc import Iterator
from datetime import datetime
from typing import Final

import httpx
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Lower
from django.db.utils import DataError
from django.utils import timezone

from radiofeed import tokenizer
from radiofeed.episodes.models import Episode
from radiofeed.feedparser import rss_parser, scheduler
from radiofeed.feedparser.date_parser import parse_date
from radiofeed.feedparser.exceptions import (
    DuplicateError,
    FeedParserError,
    InaccessibleError,
    InvalidDataError,
    NotModifiedError,
    UnavailableError,
)
from radiofeed.feedparser.models import Feed, Item
from radiofeed.http_client import Client
from radiofeed.podcasts.models import Category, Podcast


@functools.cache
def get_categories() -> dict[str, Category]:
    """Returns a cached dict of categories with lowercase names as key."""
    return {
        category.lowercase_name: category
        for category in Category.objects.annotate(lowercase_name=Lower("name"))
    }


def make_content_hash(content: bytes) -> str:
    """Hashes RSS content."""
    return hashlib.sha256(content).hexdigest()


def parse_feed(podcast: Podcast, client: Client) -> None:
    """Updates a Podcast instance with its RSS or Atom feed source."""
    _FeedParser(podcast).parse(client)


class _FeedParser:
    """Updates a Podcast instance with its RSS or Atom feed source."""

    _max_retries: Final = 3

    _accept_header: Final = (
        "application/atom+xml,"
        "application/rdf+xml,"
        "application/rss+xml,"
        "application/x-netcdf,"
        "application/xml;q=0.9,"
        "text/xml;q=0.2,"
        "*/*;q=0.1"
    )

    def __init__(self, podcast: Podcast) -> None:
        self._podcast = podcast

    def parse(self, client: Client) -> None:
        """Syncs Podcast instance with RSS or Atom feed source.

        Podcast details are updated and episodes created, updated or deleted
        accordingly.

        Raises:
            FeedParserError: if any errors found in fetching or parsing the feed.
        """
        response: httpx.Response | None = None

        content_hash: str = self._podcast.content_hash
        etag: str = self._podcast.etag
        modified: datetime | None = self._podcast.modified

        canonical: Podcast | None = None

        try:
            response = self._fetch(client)

            etag = self._parse_etag(response)
            modified = self._parse_modified(response)

            content_hash = make_content_hash(response.content)

            if content_hash == self._podcast.content_hash:
                raise NotModifiedError

            if canonical := self._find_canonical(response.url, content_hash):
                raise DuplicateError

            self._update_ok(
                feed=rss_parser.parse_rss(response.content),
                rss=response.url,
                content_hash=content_hash,
                etag=etag,
                modified=modified,
            )
        except FeedParserError as exc:
            self._update_error(
                exc,
                canonical=canonical,
                content_hash=content_hash,
                etag=etag,
                modified=modified,
            )

    def _update_ok(self, feed: Feed, **fields) -> None:
        categories_dct = get_categories()

        try:
            with transaction.atomic():
                self._update(
                    num_retries=0,
                    parser_error="",
                    active=not (feed.complete),
                    keywords=self._parse_keywords(feed, categories_dct),
                    extracted_text=self._tokenize_content(feed),
                    frequency=scheduler.schedule(feed),
                    **feed.model_dump(
                        exclude={
                            "categories",
                            "complete",
                            "items",
                        }
                    ),
                    **fields,
                )

                self._podcast.categories.set(
                    self._parse_categories(feed, categories_dct)
                )

                self._episode_updates(feed)

        except DataError as exc:
            raise InvalidDataError from exc

    def _update_error(self, exc: FeedParserError, **fields) -> None:
        frequency = self._podcast.frequency
        num_retries = self._get_retries(exc)

        if active := self._keep_active(exc, num_retries):
            frequency = scheduler.reschedule(
                self._podcast.pub_date, self._podcast.frequency
            )

        self._update(
            active=active,
            num_retries=num_retries,
            frequency=frequency,
            parser_error=exc.parser_error,
            **fields,
        )
        # re-raise original exception
        raise exc

    def _fetch(self, client: Client) -> httpx.Response:
        try:
            try:
                return client.get(
                    self._podcast.rss,
                    headers=self._build_headers(),
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.is_redirect:
                    raise NotModifiedError(response=exc.response) from exc
                if exc.response.is_client_error:
                    raise InaccessibleError(response=exc.response) from exc
                raise
        except httpx.HTTPError as exc:
            raise UnavailableError from exc

    def _find_canonical(self, url: httpx.URL, content_hash: str) -> Podcast | None:
        # check no other podcast with this RSS URL or identical content
        return (
            Podcast.objects.exclude(pk=self._podcast.pk)
            .filter(
                Q(rss=url) | Q(content_hash=content_hash),
                canonical__isnull=True,
            )
            .first()
        )

    def _parse_etag(self, response: httpx.Response) -> str:
        return response.headers.get("ETag", "")

    def _parse_modified(self, response: httpx.Response) -> datetime | None:
        return parse_date(response.headers.get("Last-Modified"))

    def _build_headers(self) -> dict[str, str]:
        return {"Accept": self._accept_header} | self._podcast.build_http_headers()

    def _update(self, **fields) -> None:
        now = timezone.now()

        Podcast.objects.filter(pk=self._podcast.pk).update(
            updated=now,
            parsed=now,
            **fields,
        )

    def _parse_keywords(self, feed: Feed, categories_dct: dict[str, Category]) -> str:
        return " ".join(
            [value for value in feed.categories if value not in categories_dct]
        )

    def _parse_categories(
        self, feed: Feed, categories_dct: dict[str, Category]
    ) -> list[Category]:
        return [
            categories_dct[value]
            for value in feed.categories
            if value in categories_dct
        ]

    def _tokenize_content(self, feed: Feed) -> str:
        text = " ".join(
            value
            for value in [
                feed.title,
                feed.description,
                feed.owner,
            ]
            + list(feed.categories)
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

        for batch in itertools.batched(self._episodes_for_update(feed, guids), 1000):
            Episode.objects.fast_update(
                batch,
                fields=[
                    "cover_url",
                    "description",
                    "duration",
                    "episode",
                    "episode_type",
                    "explicit",
                    "keywords",
                    "file_size",
                    "media_type",
                    "media_url",
                    "pub_date",
                    "season",
                    "title",
                ],
            )

        # add new episodes

        for batch in itertools.batched(self._episodes_for_insert(feed, guids), 100):
            Episode.objects.bulk_create(batch, ignore_conflicts=True)

    def _episodes_for_insert(
        self, feed: Feed, guids: dict[str, int]
    ) -> Iterator[Episode]:
        for item in feed.items:
            if item.guid not in guids:
                yield self._make_episode(item)

    def _episodes_for_update(
        self, feed: Feed, guids: dict[str, int]
    ) -> Iterator[Episode]:
        episode_ids = set()

        for item in [item for item in feed.items if item.guid in guids]:
            if (episode_id := guids[item.guid]) not in episode_ids:
                yield self._make_episode(item, episode_id)
                episode_ids.add(episode_id)

    def _make_episode(self, item: Item, episode_id: int | None = None) -> Episode:
        return Episode(
            pk=episode_id,
            podcast=self._podcast,
            **item.model_dump(exclude={"categories"}),
        )

    def _get_retries(self, exc: FeedParserError) -> int:
        match exc:
            case NotModifiedError():
                return 0

            case _:
                return self._podcast.num_retries + 1

    def _keep_active(self, exc: FeedParserError, num_retries: int) -> bool:
        match exc:
            case DuplicateError():
                return False

            case NotModifiedError():
                return True

            case _:
                return self._max_retries > num_retries
