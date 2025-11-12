import dataclasses
import functools
import itertools
import operator
from collections.abc import Iterator

from django.db import IntegrityError, transaction
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


def parse_feed(podcast: Podcast, client: Client) -> Podcast.ParserResult:
    """Updates a Podcast instance with its RSS or Atom feed source."""
    return _FeedParser(podcast=podcast).parse(client)


@functools.cache
def get_categories_dict() -> dict[str, Category]:
    """Return dict of categories with name as key."""
    return {category.name.casefold(): category for category in Category.objects.all()}


@dataclasses.dataclass(kw_only=True, frozen=True)
class _FeedParser:
    podcast: Podcast
    max_retries: int = 30

    def parse(self, client: Client) -> Podcast.ParserResult:
        """Parse the podcast's RSS feed and update the Podcast instance."""

        canonical_id: int | None = None

        etag, modified, content_hash = (
            self.podcast.etag,
            self.podcast.modified,
            self.podcast.content_hash,
        )
        updated = parsed = timezone.now()

        try:
            response = rss_fetcher.fetch_rss(
                client,
                self.podcast.rss,
                etag=etag,
                modified=modified,
            )

            etag, modified, content_hash = (
                response.etag,
                response.modified,
                response.content_hash,
            )

            # Not all feeds use ETag or Last-Modified headers correctly,
            # so we also check the content hash to see if the feed has changed.

            if content_hash == self.podcast.content_hash:
                raise NotModifiedError

            # check for duplicates based on content hash
            if canonical_id := self._get_canonical_id(
                content_hash=content_hash,
                rss=response.url,
            ):
                raise DuplicateError

            feed = rss_parser.parse_rss(response.content)
            rss = feed.canonical_url or response.url

            # Check for feed redirection and duplicates
            if rss != response.url and (
                canonical_id := self._get_canonical_id(rss=rss)
            ):
                raise DuplicateError

            return self._handle_success(
                feed=feed,
                rss=rss,
                content_hash=content_hash,
                etag=etag,
                modified=modified,
                parsed=parsed,
                updated=updated,
            )
        except FeedParserError as exc:
            return self._handle_error(
                exc,
                canonical_id=canonical_id,
                content_hash=content_hash,
                etag=etag,
                modified=modified,
                parsed=parsed,
                updated=updated,
            )

    def _handle_success(self, feed: Feed, **fields) -> Podcast.ParserResult:
        result = Podcast.ParserResult.SUCCESS
        keywords, categories = _parse_categories(feed)
        try:
            with transaction.atomic():
                Podcast.objects.filter(pk=self.podcast.pk).update(
                    num_retries=0,
                    parser_result=result,
                    active=not feed.complete,
                    num_episodes=len(feed.items),
                    extracted_text=feed.tokenize(),
                    frequency=scheduler.schedule(feed),
                    keywords=keywords,
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
                self.podcast.categories.set(categories)
                self._parse_episodes(feed)
        except (DataError, IntegrityError) as exc:
            raise InvalidDataError from exc
        return result

    def _handle_error(self, exc: FeedParserError, **fields) -> Podcast.ParserResult:
        # Handle errors when parsing a feed
        active = True
        num_retries = self.podcast.num_retries

        match exc:
            case NotModifiedError():
                # The feed has not been modified, but otherwise is OK. We can reset num_retries.
                num_retries = 0
            case DuplicateError() | DiscontinuedError():
                # The podcast is a duplicate or has been discontinued
                active = False
            case _:
                num_retries += 1
                active = num_retries < self.max_retries

        frequency = (
            scheduler.reschedule(
                self.podcast.pub_date,
                self.podcast.frequency,
            )
            if active
            else self.podcast.frequency
        )

        Podcast.objects.filter(pk=self.podcast.pk).update(
            active=active,
            num_retries=num_retries,
            frequency=frequency,
            parser_result=exc.result,
            **fields,
        )
        return exc.result

    def _get_canonical_id(self, **fields) -> int | None:
        """Return the PK of a canonical podcast matching the given fields."""
        q = functools.reduce(
            operator.or_,
            (
                Q(**{k: v})
                for k, v in fields.items()
                if v and v != getattr(self.podcast, k)
            ),
            Q(),
        )
        return (
            (
                Podcast.objects.exclude(pk=self.podcast.pk)
                .filter(q, canonical__isnull=True)
                .values_list("pk", flat=True)
                .first()
            )
            if q
            else None
        )

    def _parse_episodes(self, feed: Feed) -> None:
        """Parse the podcast's RSS feed and update the episodes."""
        # Delete any episodes that are not in the feed
        qs = Episode.objects.filter(podcast=self.podcast)
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
                fields=(
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
                ),
            )

        for batch in itertools.batched(
            self._episodes_for_insert(feed, guids),
            100,
            strict=False,
        ):
            Episode.objects.bulk_create(batch, ignore_conflicts=True)

    def _episodes_for_insert(
        self, feed: Feed, guids: dict[str, int]
    ) -> Iterator[Episode]:
        """Return episodes that are not in the database."""
        for item in feed.items:
            if item.guid not in guids:
                yield self._parse_episode(item)

    def _episodes_for_update(
        self, feed: Feed, guids: dict[str, int]
    ) -> Iterator[Episode]:
        """Return episodes that are already in the database."""
        # fast_update() requires that we have no episodes with the same PK
        episode_ids = set()
        for item in feed.items:
            if (episode_id := guids.get(item.guid)) and episode_id not in episode_ids:
                yield self._parse_episode(item, pk=episode_id)
                episode_ids.add(episode_id)

    def _parse_episode(self, item: Item, **fields) -> Episode:
        return Episode(
            podcast=self.podcast,
            **item.model_dump(exclude={"categories"}),
            **fields,
        )


def _parse_categories(feed: Feed) -> tuple[str, set[Category]]:
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
