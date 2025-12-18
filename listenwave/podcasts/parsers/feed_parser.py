import dataclasses
import functools
import itertools
from typing import Any

from django.db import transaction
from django.db.utils import DatabaseError as DatabaseBackendError
from django.utils import timezone

from listenwave.episodes.models import Episode
from listenwave.http_client import Client
from listenwave.podcasts.models import Category, Podcast
from listenwave.podcasts.parsers import rss_fetcher, rss_parser, scheduler
from listenwave.podcasts.parsers.exceptions import (
    DatabaseError,
    DiscontinuedError,
    DuplicateError,
    FeedParserError,
    InvalidRSSError,
    NotModifiedError,
    PermanentNetworkError,
)
from listenwave.podcasts.parsers.models import Feed, Item


def parse_feed(podcast: Podcast, client: Client) -> Podcast.ParserResult:
    """Updates a Podcast instance with its RSS or Atom feed source."""
    return _FeedParser(podcast=podcast).parse(client)


@functools.cache
def get_categories_dict() -> dict[str, Category]:
    """Return dict of categories with slug as key."""
    return Category.objects.in_bulk(field_name="slug")


@dataclasses.dataclass(kw_only=True, frozen=True)
class _FeedParser:
    podcast: Podcast

    def parse(self, client: Client) -> Podcast.ParserResult:
        """Parse the podcast's RSS feed and update the Podcast instance.
        Additional fields passed will update the podcast.
        """

        now = timezone.now()
        fields: dict[str, Any] = {"parsed": now, "updated": now}

        try:
            response = rss_fetcher.fetch_rss(
                client,
                self.podcast.rss,
                etag=self.podcast.etag,
                modified=self.podcast.modified,
            )

            fields.update(
                {
                    "content_hash": response.content_hash,
                    "etag": response.etag,
                    "modified": response.modified,
                }
            )

            # Not all feeds use ETag or Last-Modified headers correctly,
            # so we also check the content hash to see if the feed has changed.
            if response.content_hash == self.podcast.content_hash:
                raise NotModifiedError

            # Check for duplicate RSS feeds by URL
            self._raise_for_duplicate(response.url)

            # Generate the feed from the response content
            feed = rss_parser.parse_rss(response.content)

            # Get the canonical URL from the feed, or use the fetched URL
            canonical_rss = feed.canonical_url or response.url

            # If canonical URL in the feed differs from the fetched URL,
            # check for duplicates again.

            if canonical_rss != response.url:
                self._raise_for_duplicate(canonical_rss)

            return self._handle_success(feed=feed, rss=canonical_rss, **fields)

        except DuplicateError as exc:
            return self._handle_permanent_error(
                exc, canonical_id=exc.canonical_id, **fields
            )
        except (
            DiscontinuedError,
            InvalidRSSError,
            PermanentNetworkError,
        ) as exc:
            # These are permanent errors, so we deactivate the podcast
            return self._handle_permanent_error(exc, **fields)

        except FeedParserError as exc:
            # These are transient errors, so we reschedule the next fetch time
            return self._handle_transient_error(exc, **fields)

    def _handle_success(self, feed: Feed, **fields) -> Podcast.ParserResult:
        try:
            with transaction.atomic():
                self._parse_categories(feed)
                self._parse_episodes(feed)

                return self._update_podcast(
                    Podcast.ParserResult.SUCCESS,
                    active=not feed.complete,
                    num_episodes=len(feed.items),
                    extracted_text=feed.tokenize(),
                    frequency=scheduler.schedule(feed),
                    **feed.model_dump(
                        exclude={
                            "canonical_url",
                            "categories",
                            "complete",
                            "items",
                        }
                    ),
                    **fields,
                )
        except DatabaseBackendError as exc:
            raise DatabaseError from exc

    def _handle_transient_error(
        self, exc: FeedParserError, **fields
    ) -> Podcast.ParserResult:
        # On transient errors, we reschedule the next fetch time
        frequency = scheduler.reschedule(self.podcast.pub_date, self.podcast.frequency)
        return self._update_podcast(exc.result, frequency=frequency, **fields)

    def _handle_permanent_error(
        self, exc: FeedParserError, **fields
    ) -> Podcast.ParserResult:
        # On permanent errors, we deactivate the podcast
        return self._update_podcast(exc.result, active=False, **fields)

    def _raise_for_duplicate(self, rss: str) -> None:
        if canonical_id := (
            Podcast.objects.exclude(pk=self.podcast.pk)
            .filter(rss=rss, canonical__isnull=True)
            .values_list("pk", flat=True)
            .first()
        ):
            raise DuplicateError(canonical_id=canonical_id)

    def _update_podcast(
        self, result: Podcast.ParserResult, **fields
    ) -> Podcast.ParserResult:
        Podcast.objects.filter(pk=self.podcast.pk).update(
            parser_result=result, **fields
        )
        return result

    def _parse_categories(self, feed: Feed) -> None:
        categories_dct = get_categories_dict()
        categories = {
            categories_dct[cat] for cat in feed.categories if cat in categories_dct
        }
        self.podcast.categories.set(categories)

    def _parse_episodes(self, feed: Feed) -> None:
        """Parse the podcast's RSS feed and update the episodes."""

        episodes = Episode.objects.filter(podcast=self.podcast)

        # Delete any episodes that are not in the feed
        episodes.exclude(guid__in={item.guid for item in feed.items}).delete()

        # Create a dictionary of guids to episode pks
        guids = dict(episodes.values_list("guid", "pk"))

        # Update existing episodes
        #
        # fast_update() requires unique primary keys, do dudupe first
        items_for_update = {
            guids[item.guid]: item for item in feed.items if item.guid in guids
        }

        episodes_for_update = (
            self._parse_episode(item, pk=episode_id)
            for episode_id, item in items_for_update.items()
        )

        fields_for_update = Item.model_fields.keys()

        for batch in itertools.batched(
            episodes_for_update,
            1000,
            strict=False,
        ):
            episodes.fast_update(batch, fields=fields_for_update)

        # Insert new episodes
        #
        episodes_for_insert = (
            self._parse_episode(item) for item in feed.items if item.guid not in guids
        )

        for batch in itertools.batched(
            episodes_for_insert,
            100,
            strict=False,
        ):
            Episode.objects.bulk_create(batch, ignore_conflicts=True)

    def _parse_episode(self, item: Item, **fields) -> Episode:
        return Episode(podcast=self.podcast, **item.model_dump(), **fields)
