import dataclasses
import functools
import itertools
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from radiofeed.episodes.models import Episode
from radiofeed.podcasts.feed_parser import scheduler
from radiofeed.podcasts.feed_parser.exceptions import (
    DiscontinuedError,
    DuplicateError,
    FeedParseError,
    InvalidRSSError,
    UnavailableError,
)
from radiofeed.podcasts.feed_parser.models import Feed, Item
from radiofeed.podcasts.feed_parser.rss_fetcher import fetch_rss
from radiofeed.podcasts.feed_parser.rss_parser import parse_rss
from radiofeed.podcasts.models import Category, Podcast

if TYPE_CHECKING:
    import datetime

    from radiofeed.client import Client


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
            response = fetch_rss(self.podcast, client)

            canonical_rss = self._resolve_canonical_rss(self.podcast.rss, response.url)

            feed = parse_rss(response.content)

            if feed.canonical_url:
                canonical_rss = self._resolve_canonical_rss(
                    canonical_rss, feed.canonical_url
                )

            if feed.complete:
                active, feed_status = False, Podcast.FeedStatus.DISCONTINUED
            else:
                active, feed_status = True, Podcast.FeedStatus.SUCCESS

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
        except FeedParseError as exc:
            active = True
            canonical_id = None
            num_retries = 0

            match exc:
                case DiscontinuedError():
                    active = False
                case DuplicateError():
                    active = False
                    canonical_id = exc.canonical_id
                case InvalidRSSError() | UnavailableError():
                    active = self.podcast.num_retries < self.podcast.MAX_RETRIES
                    num_retries = self.podcast.num_retries + 1

            frequency = self._reschedule() if active else self.podcast.frequency

            return self._feed_update(
                exc.feed_status,
                active=active,
                canonical_id=canonical_id,
                frequency=frequency,
                num_retries=num_retries,
            )

    def _resolve_canonical_rss(self, current_url: str, new_url: str) -> str:
        if current_url == new_url:
            return current_url

        if root := (
            Podcast.objects.exclude(pk=self.podcast.pk)
            .filter(rss=new_url)
            .select_related("canonical")
            .only("pk", "canonical")
        ).first():
            seen: set[int] = set()

            while root.canonical:
                if root.pk in seen:
                    break
                seen.add(root.pk)
                root = root.canonical

            if root.pk == self.podcast.pk:
                return current_url

            raise DuplicateError(canonical_id=root.pk)

        return new_url

    def _reschedule(self) -> datetime.timedelta:
        return scheduler.reschedule(self.podcast.pub_date, self.podcast.frequency)

    def _feed_update(
        self,
        feed_status: Podcast.FeedStatus,
        *,
        active=True,
        num_retries: int = 0,
        **fields,
    ) -> Podcast.FeedStatus:
        now = timezone.now()
        Podcast.objects.filter(pk=self.podcast.pk).update(
            feed_status=feed_status,
            active=active,
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

        episodes = Episode.objects.filter(podcast=self.podcast)

        items = {item.guid: item for item in feed.items}.values()

        episodes.exclude(guid__in={item.guid for item in items}).delete()

        guids_to_pks = dict(episodes.values_list("guid", "pk"))

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
