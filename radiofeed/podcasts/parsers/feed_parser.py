import dataclasses
import datetime
import functools
import itertools
from typing import Any

from django.db import transaction
from django.utils import timezone

from radiofeed.episodes.models import Episode
from radiofeed.http_client import Client
from radiofeed.podcasts.models import Category, Podcast
from radiofeed.podcasts.parsers import rss_fetcher, rss_parser, scheduler
from radiofeed.podcasts.parsers.models import Feed, Item
from radiofeed.podcasts.parsers.rss_fetcher import DiscontinuedError, NotModifiedError


def parse_feed(podcast: Podcast, client: Client) -> None:
    """Updates a Podcast instance with its RSS or Atom feed source."""
    _FeedParser(podcast=podcast).parse(client)


@functools.cache
def get_categories_dict() -> dict[str, Category]:
    """Return dict of categories with slug as key."""
    return Category.objects.in_bulk(field_name="slug")


class DuplicateError(Exception):
    """Another identical podcast exists in the database."""

    def __init__(self, *args, canonical_id: int | None = None, **kwargs):
        self.canonical_id = canonical_id
        super().__init__(*args, **kwargs)


@dataclasses.dataclass(kw_only=True, frozen=True)
class _FeedParser:
    podcast: Podcast

    def parse(self, client: Client) -> None:
        """Parse the podcast's RSS feed and update the Podcast instance.
        Additional fields passed will update the podcast.
        """

        now = timezone.now()

        fields: dict[str, Any] = {
            "parsed": now,
            "updated": now,
            "exception": "",
        }

        try:
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

            with transaction.atomic():
                self._update_podcast(
                    active=not (feed.complete),
                    rss=canonical_rss,
                    feed_last_updated=now,
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
        except DiscontinuedError:
            self._update_podcast(active=False, **fields)
        except DuplicateError as exc:
            self._update_podcast(active=False, canonical_id=exc.canonical_id, **fields)
        except NotModifiedError:
            self._update_podcast(frequency=self._reschedule(), **fields)
        except Exception as exc:
            fields["exception"] = f"{exc.__class__.__name__}: {exc}"
            self._update_podcast(frequency=self._reschedule(), **fields)
            raise

    def _raise_for_duplicate(self, rss: str) -> None:
        if canonical_id := (
            Podcast.objects.exclude(pk=self.podcast.pk)
            .filter(rss=rss, canonical__isnull=True)
            .values_list("pk", flat=True)
            .first()
        ):
            raise DuplicateError("Duplicate", canonical_id=canonical_id)

    def _reschedule(self) -> datetime.timedelta:
        return scheduler.reschedule(
            self.podcast.pub_date,
            self.podcast.frequency,
        )

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
