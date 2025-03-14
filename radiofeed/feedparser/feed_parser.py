import itertools
from collections.abc import Iterator
from typing import Final

from django.db import transaction
from django.db.models import Q
from django.db.utils import DataError
from django.utils import timezone

from radiofeed.episodes.models import Episode
from radiofeed.feedparser import rss_fetcher, rss_parser, scheduler
from radiofeed.feedparser.exceptions import (
    DuplicateError,
    FeedParserError,
    InvalidDataError,
    NotModifiedError,
)
from radiofeed.feedparser.models import Feed, Item
from radiofeed.http_client import Client
from radiofeed.podcasts.models import Category, Podcast


def parse_feed(podcast: Podcast, client: Client) -> None:
    """Updates a Podcast instance with its RSS or Atom feed source."""
    _FeedParser(podcast).parse(client)


class _FeedParser:
    """Updates a Podcast instance with its RSS or Atom feed source."""

    _max_retries: Final = 3

    def __init__(self, podcast: Podcast) -> None:
        self._podcast = podcast

    def parse(self, client: Client) -> None:
        """Syncs Podcast instance with RSS or Atom feed source.

        Podcast details are updated and episodes created, updated or deleted
        accordingly.

        Raises:
            FeedParserError: if any errors found in fetching or parsing the feed.
        """

        canonical = None

        etag = self._podcast.etag
        modified = self._podcast.modified
        content_hash = self._podcast.content_hash

        try:
            response = rss_fetcher.fetch_rss(
                client,
                self._podcast.rss,
                etag=etag,
                modified=modified,
            )

            etag = response.etag
            modified = response.modified
            content_hash = response.content_hash

            # check if feed has been modified: usually the feed should return a 304 status,
            # but some feeds may not support this so we check the content hash
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
        category_dct = _get_categories_dict()
        try:
            with transaction.atomic():
                self._update(
                    num_retries=0,
                    parser_error="",
                    active=not (feed.complete),
                    extracted_text=feed.tokenize(),
                    keywords=_parse_keywords(feed, category_dct),
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
                self._podcast.categories.set(_parse_categories(feed, category_dct))
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

    def _update(self, **fields) -> None:
        now = timezone.now()

        Podcast.objects.filter(pk=self._podcast.pk).update(
            updated=now,
            parsed=now,
            **fields,
        )

    def _find_canonical(self, url: str, content_hash: str) -> Podcast | None:
        # check no other podcast with this RSS URL or identical content
        return (
            Podcast.objects.exclude(pk=self._podcast.pk)
            .filter(
                Q(rss=url) | Q(content_hash=content_hash),
                canonical__isnull=True,
            )
            .first()
        )

    def _episode_updates(self, feed: Feed) -> None:
        qs = Episode.objects.filter(podcast=self._podcast)

        # remove any episodes that may have been deleted on the podcast
        qs.exclude(guid__in={item.guid for item in feed.items}).delete()

        # determine new/current items based on presence of guid

        guids = dict(qs.values_list("guid", "pk"))

        # update existing content

        for batch in itertools.batched(
            self._episodes_for_update(feed, guids),
            1000,
            strict=False,
        ):
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

        for batch in itertools.batched(
            self._episodes_for_insert(feed, guids),
            100,
            strict=False,
        ):
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


def _parse_categories(feed: Feed, category_dict: dict[str, Category]) -> set[Category]:
    return {
        category_dict[category]
        for category in feed.categories
        if category in category_dict
    }


def _parse_keywords(feed: Feed, category_dict: dict[str, Category]) -> str:
    return " ".join(feed.categories - set(category_dict.keys()))


def _get_categories_dict() -> dict[str, Category]:
    return {
        category.name.casefold(): category for category in Category.objects.from_cache()
    }
