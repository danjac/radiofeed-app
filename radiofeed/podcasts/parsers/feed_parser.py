import dataclasses
import datetime
import functools
import itertools

from django.db import transaction
from django.db.utils import DatabaseError
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


def parse_feed(podcast: Podcast, client: Client) -> Podcast.FeedStatus:
    """Updates a Podcast instance with its RSS or Atom feed source."""
    return _FeedParser(podcast=podcast).parse(client)


@functools.cache
def get_categories_dict() -> dict[str, Category]:
    """Return dict of categories with slug as key."""
    return Category.objects.in_bulk(field_name="slug")


@dataclasses.dataclass(kw_only=True, frozen=True)
class _FeedParser:
    podcast: Podcast

    def parse(self, client: Client) -> Podcast.FeedStatus:
        """Parse the podcast's RSS feed and update the Podcast instance."""

        try:
            # Fetch RSS feed
            response = rss_fetcher.fetch_rss(self.podcast, client)

            # Check for duplicate RSS feeds
            self._raise_for_duplicate(response.url)

            # Parse RSS feed
            feed = rss_parser.parse_rss(response.content)

            # Check for canonical RSS URL changes if new canonical url in feed
            canonical_rss = feed.canonical_url or response.url
            if canonical_rss != response.url:
                self._raise_for_duplicate(canonical_rss)

            # Determine podcast active status
            if feed.complete:
                active, feed_status = False, Podcast.FeedStatus.DISCONTINUED
            else:
                active, feed_status = True, Podcast.FeedStatus.SUCCESS

            # Persist and parse categories/episodes atomically
            with transaction.atomic():
                self._parse_categories(feed)
                self._parse_episodes(feed)

                return self._feed_update(
                    feed_status,
                    active=active,
                    rss=canonical_rss,
                    feed_last_updated=timezone.now(),
                    num_episodes=len(feed.items),
                    content_hash=response.content_hash,
                    etag=response.etag,
                    modified=response.modified,
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
                )

        except DatabaseError as exc:
            # -- Handle database write errors
            # -- Update feed status to ERROR and reschedule next fetch
            # Log exception for debugging
            return self._feed_update(
                feed_status=Podcast.FeedStatus.DATABASE_ERROR,
                frequency=self._reschedule(),
                exception=str(exc),
            )

        except NotModifiedError:
            # -- Handle not modified RSS feed
            # -- Update feed status to NOT_MODIFIED and reschedule next fetch
            return self._feed_update(
                Podcast.FeedStatus.NOT_MODIFIED,
                frequency=self._reschedule(),
            )

        except DiscontinuedError:
            # -- Handle discontinued podcast feeds
            # -- Deactivate podcast and set feed status to DISCONTINUED
            return self._feed_update(Podcast.FeedStatus.DISCONTINUED, active=False)

        except DuplicateError as exc:
            # -- Handle duplicate RSS feed errors
            # -- Deactivate podcast and set feed status to DUPLICATE
            return self._feed_update(
                feed_status=Podcast.FeedStatus.DUPLICATE,
                active=False,
                canonical_id=exc.canonical_id,
            )

        except (InvalidRSSError, UnavailableError) as exc:
            # -- Handle recoverable errors with retry logic
            # Determine if podcast should remain active
            # -- If max retries exceeded, deactivate podcast
            # -- Otherwise, reschedule next fetch based on retry logic
            # Log exception for debugging

            active = self.podcast.num_retries < self.podcast.MAX_RETRIES
            frequency = self._reschedule() if active else self.podcast.frequency
            num_retries = self.podcast.num_retries + 1

            match exc:
                case InvalidRSSError():
                    feed_status = Podcast.FeedStatus.INVALID_RSS
                case UnavailableError():
                    feed_status = Podcast.FeedStatus.UNAVAILABLE

            return self._feed_update(
                feed_status,
                active=active,
                frequency=frequency,
                num_retries=num_retries,
                exception=str(exc),
            )

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

    def _feed_update(
        self,
        feed_status: Podcast.FeedStatus,
        *,
        active=True,
        exception: str = "",
        num_retries: int = 0,
        **fields,
    ) -> Podcast.FeedStatus:
        now = timezone.now()
        Podcast.objects.filter(pk=self.podcast.pk).update(
            feed_status=feed_status,
            active=active,
            exception=exception,
            num_retries=num_retries,
            updated=now,
            parsed=now,
            **fields,
        )
        return feed_status

    def _parse_categories(self, feed: Feed) -> None:
        categories_dct = get_categories_dict()
        categories = {
            categories_dct[cat] for cat in feed.categories if cat in categories_dct
        }
        self.podcast.categories.set(categories)

    def _parse_episodes(self, feed: Feed, batch_size: int = 100) -> None:
        """Parse the podcast's RSS feed and update the episodes."""

        episodes = Episode.objects.filter(podcast=self.podcast)

        # Delete any episodes that are not in the feed
        episodes.exclude(guid__in={item.guid for item in feed.items}).delete()

        # Create a dictionary of guids to episode pks
        guids = dict(episodes.values_list("guid", "pk"))

        # Update existing episodes
        items_for_update = {
            guids[item.guid]: item for item in feed.items if item.guid in guids
        }

        episodes_for_update = (
            self._parse_episode(item, pk=episode_id)
            for episode_id, item in items_for_update.items()
        )

        fields_for_update = Item.model_fields.keys()

        for batch in itertools.batched(episodes_for_update, batch_size, strict=False):
            episodes.fast_update(batch, fields=fields_for_update)

        # Insert new episodes
        episodes_for_insert = (
            self._parse_episode(item) for item in feed.items if item.guid not in guids
        )

        for batch in itertools.batched(episodes_for_insert, batch_size, strict=False):
            Episode.objects.bulk_create(batch, ignore_conflicts=True)

    def _parse_episode(self, item: Item, **fields) -> Episode:
        return Episode(podcast=self.podcast, **item.model_dump(), **fields)
