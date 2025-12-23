import dataclasses
import datetime
import functools
import itertools
from typing import Any

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from radiofeed.episodes.models import Episode
from radiofeed.http_client import Client
from radiofeed.podcasts.models import Category, Podcast
from radiofeed.podcasts.parsers import rss_fetcher, rss_parser, scheduler
from radiofeed.podcasts.parsers.exceptions import (
    DiscontinuedError,
    DuplicateError,
    InvalidRSSError,
    NotModifiedError,
    UnavailableError,
)
from radiofeed.podcasts.parsers.models import Feed, Item


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
        """

        now = timezone.now()

        # Common fields to update:
        # - parsed: timestamp of this parse attempt
        # - updated: timestamp of last successful update
        # - exception: clear last exception message
        # - num_retries: reset retry counter to zero
        fields: dict[str, Any] = {
            "exception": "",
            "num_retries": 0,
            "parsed": now,
            "updated": now,
        }

        try:
            # Fetch the RSS feed
            response = rss_fetcher.fetch_rss(self.podcast, client)

            fields.update(
                {
                    "content_hash": response.content_hash,
                    "etag": response.etag,
                    "modified": response.modified,
                }
            )

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

            # If feed is marked complete, set podcast as inactive. However
            # we still want to update the feed data for the last time.
            if feed.complete:
                active, feed_status = False, Podcast.FeedStatus.DISCONTINUED
            else:
                active, feed_status = True, Podcast.FeedStatus.SUCCESS

            # Successful update:
            # - update podcast fields from the feed
            # - update categories
            # - update episodes
            # - set feed_last_updated to now

            fields.update(
                {
                    "active": active,
                    "feed_status": feed_status,
                    "rss": canonical_rss,
                    "feed_last_updated": now,
                    "num_episodes": len(feed.items),
                    "extracted_text": feed.tokenize(),
                    "frequency": scheduler.schedule(feed),
                }
            )

            # Parse rest of feed
            fields.update(
                feed.model_dump(
                    exclude={
                        "canonical_url",
                        "categories",
                        "complete",
                        "items",
                    }
                )
            )

            with transaction.atomic():
                self._update_podcast(**fields)
                self._parse_categories(feed)
                self._parse_episodes(feed)
        except NotModifiedError as exc:
            # RSS feed has not changed since last update:
            #  - reschedule the next fetch
            fields.update(
                {
                    "feed_status": exc.feed_status,
                    "frequency": self._reschedule(),
                }
            )
            self._update_podcast(**fields)
        except DiscontinuedError as exc:
            # Podcast has been marked discontinued:
            # - mark this podcast as inactive
            fields.update(
                {
                    "active": False,
                    "feed_status": exc.feed_status,
                }
            )
            self._update_podcast(**fields)
        except DuplicateError as exc:
            # Another podcast with the same RSS feed exists:
            # - mark this podcast as inactive
            # - set the canonical podcast ID
            fields.update(
                {
                    "active": False,
                    "feed_status": exc.feed_status,
                    "canonical_id": exc.canonical_id,
                }
            )
            self._update_podcast(**fields)
        except (InvalidRSSError, UnavailableError) as exc:
            # RSS feed is invalid or temporarily unavailable:
            #  = increment the retry counter
            #  - mark podcast as inactive if max retries exceeded
            #  - log the exception message in the podcast
            #  - reschedule the next fetch if still active

            active = self.podcast.num_retries < self.podcast.MAX_RETRIES
            frequency = self._reschedule() if active else self.podcast.frequency
            num_retries = F("num_retries") + 1

            fields.update(
                {
                    "active": active,
                    "feed_status": exc.feed_status,
                    "frequency": frequency,
                    "num_retries": num_retries,
                    "exception": str(exc),
                }
            )
            self._update_podcast(**fields)
        except Exception as exc:
            # Any other exception:
            #  - log the exception message in the podcast
            #  - reschedule the next fetch
            #  - re-raise the exception

            fields.update(
                {
                    "feed_status": Podcast.FeedStatus.ERROR,
                    "frequency": self._reschedule(),
                    "exception": f"{exc.__class__.__name__}: {exc}",
                }
            )
            self._update_podcast(**fields)
            raise

    def _raise_for_duplicate(self, rss: str) -> None:
        if canonical_id := (
            Podcast.objects.exclude(pk=self.podcast.pk)
            .filter(rss=rss, canonical__isnull=True)
            .values_list("pk", flat=True)
            .first()
        ):
            raise DuplicateError(canonical_id=canonical_id)

    def _reschedule(self) -> datetime.timedelta:
        return scheduler.reschedule(self.podcast.pub_date, self.podcast.frequency)

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
        # fast_update() requires unique primary keys, do dedupe first
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
