import functools
import itertools
from collections.abc import Iterator

from django.db import transaction
from django.db.models import Q
from django.db.utils import DataError
from django.utils import timezone

from radiofeed.episodes.models import Episode
from radiofeed.feedparser import rss_fetcher, rss_parser, scheduler
from radiofeed.feedparser.exceptions import (
    DiscontinuedError,
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


@functools.cache
def get_categories_dict() -> dict[str, Category]:
    """Return dict of categories with name as key."""
    return {category.name.casefold(): category for category in Category.objects.all()}


class _FeedParser:
    def __init__(self, podcast: Podcast) -> None:
        self._podcast = podcast

    def parse(self, client: Client) -> None:
        canonical = None

        etag, modified, content_hash = (
            self._podcast.etag,
            self._podcast.modified,
            self._podcast.content_hash,
        )
        updated = parsed = timezone.now()

        try:
            response = rss_fetcher.fetch_rss(
                client,
                self._podcast.rss,
                etag=etag,
                modified=modified,
            )

            etag, modified, content_hash = (
                response.etag,
                response.modified,
                response.content_hash,
            )

            if content_hash == self._podcast.content_hash:
                raise NotModifiedError

            if canonical := self._get_canonical(response.url, content_hash):
                raise DuplicateError

            self._handle_success(
                feed=rss_parser.parse_rss(response.content),
                rss=response.url,
                content_hash=content_hash,
                etag=etag,
                modified=modified,
                parsed=parsed,
                updated=updated,
            )
        except FeedParserError as exc:
            self._handle_error(
                exc,
                canonical=canonical,
                content_hash=content_hash,
                etag=etag,
                modified=modified,
                parsed=parsed,
                updated=updated,
            )

    def _handle_success(self, feed: Feed, **fields) -> None:
        keywords, categories = self._parse_categories(feed)
        try:
            with transaction.atomic():
                self._update(
                    num_retries=0,
                    parser_error="",
                    active=not feed.complete,
                    extracted_text=feed.tokenize(),
                    frequency=scheduler.schedule(feed),
                    keywords=keywords,
                    **feed.model_dump(
                        exclude={
                            "categories",
                            "complete",
                            "items",
                        }
                    ),
                    **fields,
                )
                self._podcast.categories.set(categories)
                self._sync_episodes(feed)
        except DataError as exc:
            raise InvalidDataError from exc

    def _handle_error(self, exc: FeedParserError, **fields) -> None:
        # Handle errors when parsing a feed
        active = True
        num_retries = self._podcast.num_retries

        match exc:
            case NotModifiedError():
                # The feed has not been modified, but otherwise is OK. We can reset num_retries.
                num_retries = 0
            case DuplicateError() | DiscontinuedError():
                # The podcast is a duplicate or has been discontinued
                active = False
            case _:
                num_retries += 1

        frequency = (
            scheduler.reschedule(
                self._podcast.pub_date,
                self._podcast.frequency,
            )
            if active
            else self._podcast.frequency
        )

        self._update(
            active=active,
            num_retries=num_retries,
            frequency=frequency,
            parser_error=exc.parser_error,
            **fields,
        )
        raise exc

    def _update(self, **fields) -> None:
        # Update the podcast with the new fields
        Podcast.objects.filter(pk=self._podcast.pk).update(**fields)

    def _get_canonical(self, url: str, content_hash: str) -> Podcast | None:
        # Get the canonical podcast if it exists: matches the RSS feed URL or content hash
        return (
            Podcast.objects.exclude(pk=self._podcast.pk)
            .filter(
                Q(rss=url) | Q(content_hash=content_hash),
                canonical__isnull=True,
            )
            .first()
        )

    def _parse_categories(self, feed: Feed) -> tuple[str, set[Category]]:
        # Parse categories from the feed: return keywords and Category instances
        categories_dct = get_categories_dict()

        # Get the categories that are in the database
        categories = {
            categories_dct[category]
            for category in feed.categories
            if category in categories_dct
        }

        # Get the keywords that are not in the database
        keywords = " ".join(feed.categories - set(categories_dct.keys()))

        return keywords, categories

    def _sync_episodes(self, feed: Feed) -> None:
        # Update and insert episodes in the database

        # Delete any episodes that are not in the feed
        qs = Episode.objects.filter(podcast=self._podcast)
        qs.exclude(guid__in={item.guid for item in feed.items}).delete()

        # Create a dictionary of guids to episode pks
        guids = dict(qs.values_list("guid", "pk"))

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

        for batch in itertools.batched(
            self._episodes_for_insert(feed, guids),
            100,
            strict=False,
        ):
            Episode.objects.bulk_create(batch, ignore_conflicts=True)

    def _episodes_for_update(
        self, feed: Feed, guids: dict[str, int]
    ) -> Iterator[Episode]:
        # Return all episodes that are already in the database
        # fast_update() requires that we have no episodes with the same PK
        episode_ids = set()
        for item in feed.items:
            episode_id = guids.get(item.guid)
            if episode_id and episode_id not in episode_ids:
                yield self._make_episode(item, pk=episode_id)
                episode_ids.add(episode_id)

    def _episodes_for_insert(
        self, feed: Feed, guids: dict[str, int]
    ) -> Iterator[Episode]:
        # Return all episodes that are not in the database
        for item in feed.items:
            if item.guid not in guids:
                yield self._make_episode(item)

    def _make_episode(self, item: Item, **fields) -> Episode:
        # Build Episode instance from a feed item
        return Episode(
            podcast=self._podcast,
            **item.model_dump(exclude={"categories"}),
            **fields,
        )
