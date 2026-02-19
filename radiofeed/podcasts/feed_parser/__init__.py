import dataclasses
import functools
import itertools
from typing import TYPE_CHECKING, Final

from asgiref.sync import sync_to_async
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
from radiofeed.podcasts.feed_parser.rss_fetcher import Response, fetch_rss
from radiofeed.podcasts.feed_parser.rss_parser import parse_rss
from radiofeed.podcasts.models import Category, Podcast

if TYPE_CHECKING:
    import datetime

    from radiofeed.client import Client

_CATEGORIES_CACHE_KEY: Final = "feed_parser:categories_dict"
_CATEGORIES_CACHE_TIMEOUT: Final = 60 * 60  # 1 hour


async def parse_feed(podcast: Podcast, client: Client) -> Podcast.FeedStatus:
    """Updates a Podcast instance with its RSS or Atom feed source."""
    return await _FeedParser(podcast=podcast).parse(client)


@functools.cache
def get_categories_dict() -> dict[str, Category]:
    """Return dict of categories with slug as key, cached for one hour."""
    return dict(Category.objects.in_bulk(field_name="slug"))


@dataclasses.dataclass(kw_only=True, frozen=True)
class _FeedParser:
    podcast: Podcast

    async def parse(self, client: Client) -> Podcast.FeedStatus:
        """Parse the podcast's RSS feed and update the Podcast instance."""

        try:
            response = await fetch_rss(self.podcast, client)

            canonical_rss = await self._resolve_canonical_rss(
                self.podcast.rss, response.url
            )

            feed = parse_rss(response.content)

            if feed.canonical_url:
                canonical_rss = await self._resolve_canonical_rss(
                    canonical_rss, feed.canonical_url
                )

            if feed.complete:
                active, feed_status = False, Podcast.FeedStatus.DISCONTINUED
            else:
                active, feed_status = True, Podcast.FeedStatus.SUCCESS

            return await sync_to_async(self._sync_update)(
                feed=feed,
                feed_status=feed_status,
                active=active,
                canonical_rss=canonical_rss,
                response=response,
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

            return await sync_to_async(self._feed_update)(
                exc.feed_status,
                active=active,
                canonical_id=canonical_id,
                frequency=frequency,
                num_retries=num_retries,
            )

    async def _resolve_canonical_rss(self, current_url: str, new_url: str) -> str:
        if current_url == new_url:
            return current_url

        if root := await (
            Podcast.objects.exclude(pk=self.podcast.pk)
            .filter(rss=new_url)
            .select_related("canonical")
            .only("pk", "canonical")
        ).afirst():
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

    def _sync_update(
        self,
        *,
        feed: Feed,
        response: Response,
        feed_status: Podcast.FeedStatus,
        active: bool,
        canonical_rss: str,
    ) -> Podcast.FeedStatus:
        """Run all transactional DB writes synchronously inside a single atomic block."""
        categories_dct = get_categories_dict()

        categories = {
            categories_dct[cat] for cat in feed.categories if cat in categories_dct
        }

        with transaction.atomic():
            self.podcast.categories.set(categories)

            episodes = Episode.objects.filter(podcast=self.podcast)
            items = list({item.guid: item for item in feed.items}.values())

            episodes.exclude(guid__in={item.guid for item in items}).delete()

            guids_to_pks = dict(episodes.values_list("guid", "pk"))

            episodes_for_upsert = [
                Episode(
                    podcast=self.podcast,
                    pk=guids_to_pks.get(item.guid),
                    **item.model_dump(),
                )
                for item in items
            ]

            unique_fields = ("podcast", "guid")
            update_fields = Item.model_fields.keys()

            for batch in itertools.batched(episodes_for_upsert, 300, strict=False):
                Episode.objects.bulk_create(
                    batch,
                    update_conflicts=True,
                    unique_fields=unique_fields,
                    update_fields=update_fields,
                )

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

    def _feed_update(
        self,
        feed_status: Podcast.FeedStatus,
        *,
        active: bool = True,
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
