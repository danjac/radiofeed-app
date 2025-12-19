import dataclasses
import functools
import itertools
from typing import Any

from django.db import transaction
from django.db.utils import DatabaseError
from django.utils import timezone

from listenwave.episodes.models import Episode
from listenwave.http_client import Client
from listenwave.podcasts.models import Category, Podcast
from listenwave.podcasts.parsers import rss_fetcher, rss_parser, scheduler
from listenwave.podcasts.parsers.exceptions import (
    DatabaseOperationError,
    DiscontinuedError,
    DuplicateError,
    FeedParserError,
    InvalidRSSError,
    NotModifiedError,
    PermanentNetworkError,
)
from listenwave.podcasts.parsers.models import Feed, Item


def parse_feed(podcast: Podcast, client: Client) -> None:
    """Updates a Podcast instance with its RSS or Atom feed source."""
    _FeedParser(podcast=podcast).parse(client)


@functools.cache
def get_categories_dict() -> dict[str, Category]:
    """Return dict of categories with slug as key."""
    return Category.objects.in_bulk(field_name="slug")


@dataclasses.dataclass(kw_only=True, frozen=True)
class _FeedParser:
    podcast: Podcast

    def parse(self, client: Client) -> None:
        """Parse the podcast's RSS feed and update the Podcast instance.
        Additional fields passed will update the podcast.

        Raises FeedParserError on error.
        """

        now = timezone.now()
        fields: dict[str, Any] = {"parsed": now, "updated": now}

        try:
            try:
                response = rss_fetcher.fetch_rss(
                    client,
                    self.podcast.rss,
                    etag=self.podcast.etag,
                    modified=self.podcast.modified,
                )

            except FeedParserError as exc:
                # Capture HTTP status code if available
                if exc.response:
                    fields["http_status"] = exc.response.status_code
                raise

            fields.update(
                {
                    "content_hash": response.content_hash,
                    "etag": response.etag,
                    "http_status": response.status_code,
                    "modified": response.modified,
                }
            )

            # Not all feeds use ETag or Last-Modified headers correctly,
            # so we also check the content hash to see if the feed has changed.
            if response.content_hash == self.podcast.content_hash:
                raise NotModifiedError("Not Modified")

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

            # All ok, update the podcast and episodes
            try:
                with transaction.atomic():
                    self._update_podcast(
                        rss=canonical_rss,
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
                    self._parse_categories(feed)
                    self._parse_episodes(feed)

            except DatabaseError as exc:
                raise DatabaseOperationError from exc

        except DuplicateError as exc:
            # Deactivate the podcast if it's a duplicate
            self._update_podcast(canonical_id=exc.canonical_id, active=False, **fields)
            raise
        except (
            DiscontinuedError,
            InvalidRSSError,
            PermanentNetworkError,
        ):
            # These are permanent errors, so we deactivate the podcast
            self._update_podcast(active=False, **fields)
            raise
        except FeedParserError:
            # These are transient errors, so we reschedule the next fetch time
            frequency = scheduler.reschedule(
                self.podcast.pub_date,
                self.podcast.frequency,
            )
            self._update_podcast(frequency=frequency, **fields)
            raise

    def _raise_for_duplicate(self, rss: str) -> None:
        if canonical_id := (
            Podcast.objects.exclude(pk=self.podcast.pk)
            .filter(rss=rss, canonical__isnull=True)
            .values_list("pk", flat=True)
            .first()
        ):
            raise DuplicateError("Duplicate", canonical_id=canonical_id)

    def _update_podcast(self, **fields) -> None:
        Podcast.objects.filter(pk=self.podcast.pk).update(**fields)

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
