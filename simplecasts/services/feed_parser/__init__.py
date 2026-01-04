import dataclasses
import datetime
import functools
import itertools

from django.db import transaction
from django.db.utils import DatabaseError
from django.utils import timezone

from simplecasts.models import Category, Episode, Podcast
from simplecasts.services.feed_parser import rss_fetcher, rss_parser, scheduler
from simplecasts.services.feed_parser.exceptions import (
    DiscontinuedError,
    DuplicateError,
    InvalidRSSError,
    NotModifiedError,
    UnavailableError,
)
from simplecasts.services.feed_parser.schemas import Feed, Item
from simplecasts.services.http_client import Client


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
            canonical_rss = self._resolve_canonical_rss(self.podcast.rss, response.url)

            # Parse RSS feed
            feed = rss_parser.parse_rss(response.content)

            # Resolve canonical URL if provided in feed
            if feed.canonical_url:
                canonical_rss = self._resolve_canonical_rss(
                    canonical_rss, feed.canonical_url
                )

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
                    content_hash=response.content_hash,
                    etag=response.etag,
                    modified=response.modified,
                    extracted_text=feed.tokenize(),
                    frequency=scheduler.schedule(feed),
                    num_episodes=len(feed.items),
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
                Podcast.FeedStatus.DATABASE_ERROR,
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
                Podcast.FeedStatus.DUPLICATE,
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

    def _resolve_canonical_rss(self, current_url: str, new_url: str) -> str:
        # Resolve a new canonical RSS feed URL, checking for duplicates
        if current_url == new_url:
            return current_url

        # Check for duplicate RSS feeds in the database
        if root := (
            Podcast.objects.exclude(pk=self.podcast.pk)
            .filter(rss=new_url)
            .select_related("canonical")
            .only("pk", "canonical")
        ).first():
            # Keep track of seen podcast pks to avoid infinite loops
            seen: set[int] = set()

            # Traverse canonical chain to find root podcast
            while root.canonical:
                if root.pk in seen:
                    break
                seen.add(root.pk)
                root = root.canonical

            # If root podcast is the same as current podcast, return the original RSS
            if root.pk == self.podcast.pk:
                return current_url

            # Raise DuplicateError with root podcast's pk
            raise DuplicateError(canonical_id=root.pk)

        # No duplicate found, return the new url
        return new_url

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

    def _parse_episodes(self, feed: Feed) -> None:
        """Parse the podcast's RSS feed and update the episodes."""

        # Find existing episodes for the podcast
        episodes = Episode.objects.filter(podcast=self.podcast)

        # Ensure unique guids in feed items
        items = {item.guid: item for item in feed.items}.values()

        # Delete any episodes that are not in the feed
        episodes.exclude(guid__in={item.guid for item in items}).delete()

        # Create a dictionary of guids to episode pks
        guids_to_pks = dict(episodes.values_list("guid", "pk"))

        # Prepare episodes for upsert: map feed items to Episode instances
        episodes_for_upsert = (
            Episode(
                podcast=self.podcast,
                pk=guids_to_pks.get(item.guid),
                **item.model_dump(),
            )
            for item in items
        )

        unique_fields = ("podcast", "guid")
        update_fields = Item.model_fields.keys()

        # Bulk upsert episodes in batches
        for batch in itertools.batched(
            episodes_for_upsert,
            300,
            strict=False,
        ):
            Episode.objects.bulk_create(
                batch,
                update_conflicts=True,
                unique_fields=unique_fields,
                update_fields=update_fields,
            )
