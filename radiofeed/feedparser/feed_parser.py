import http

from typing import Generator

import attrs
import requests

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.http import http_date, quote_etag

from radiofeed.common.utils.crypto import make_content_hash
from radiofeed.common.utils.dates import parse_date
from radiofeed.common.utils.iterators import batcher
from radiofeed.common.utils.text import tokenize
from radiofeed.episodes.models import Episode
from radiofeed.feedparser.exceptions import DuplicateFeed, NotModified, RssParserError
from radiofeed.feedparser.models import Feed, Item
from radiofeed.feedparser.rss_parser import parse_rss
from radiofeed.podcasts.models import Category, Podcast


class FeedParser:
    """Updates a Podcast instance with its RSS or Atom feed source.

    Args:
        podcast (Podcast)
    """

    _feed_attrs = attrs.fields(Feed)
    _item_attrs = attrs.fields(Item)

    def __init__(self, podcast: Podcast):
        self._podcast = podcast

    @transaction.atomic
    def parse(self) -> bool:
        """Updates Podcast instance with RSS or Atom feed source.

        Podcast details are updated and episodes created, updated or deleted accordingly.

        If a podcast is discontinued (e.g. there is a duplicate feed in the database, or the feed is marked as complete) then the podcast is set inactive.

        Returns:
            if podcast has been successfully updated. This will be False if there are no new updates or there is some other problem e.g. HTTP error.
        """
        try:
            return self._handle_success(*self._parse_rss())

        except Exception as e:
            return self._handle_failure(e)

    def _parse_rss(self) -> tuple[requests.Response, Feed, str]:
        response = requests.get(
            self._podcast.rss,
            headers=self._get_feed_headers(),
            allow_redirects=True,
            timeout=10,
        )

        response.raise_for_status()

        if response.status_code == http.HTTPStatus.NOT_MODIFIED:
            raise NotModified(response=response)

        # check if another feed already has new URL
        if response.url != self._podcast.rss and Podcast.objects.filter(rss=response.url).exists():
            raise DuplicateFeed(response=response)

        # check if content has changed (feed is not checking etag etc)
        if (content_hash := make_content_hash(response.content)) == self._podcast.content_hash:
            raise NotModified(response=response)

        # check if another feed has exact same content
        if (Podcast.objects.exclude(pk=self._podcast.id).filter(content_hash=content_hash, active=True)).exists():
            raise DuplicateFeed(response=response)

        return response, parse_rss(response.content), content_hash

    def _get_feed_headers(self) -> dict:
        headers = {
            "Accept": "application/atom+xml,application/rdf+xml,application/rss+xml,application/x-netcdf,application/xml;q=0.9,text/xml;q=0.2,*/*;q=0.1",
            "User-Agent": settings.USER_AGENT,
        }

        if self._podcast.etag:
            headers["If-None-Match"] = quote_etag(self._podcast.etag)
        if self._podcast.modified:
            headers["If-Modified-Since"] = http_date(self._podcast.modified.timestamp())
        return headers

    def _handle_success(self, response: requests.Response, feed: Feed, content_hash: str) -> bool:

        # taxonomy
        categories_dct = Category.objects.in_bulk(field_name="name")

        categories = [categories_dct[category] for category in feed.categories if category in categories_dct]

        keywords = " ".join(category for category in feed.categories if category not in categories_dct)

        # mark inactive if discontinued
        if feed.complete:
            active = False
            parse_result = Podcast.ParseResult.COMPLETE
        else:
            active = True
            parse_result = Podcast.ParseResult.SUCCESS

        self._save_podcast(
            active=active,
            content_hash=content_hash,
            rss=response.url,
            etag=response.headers.get("ETag", ""),
            http_status=response.status_code,
            modified=parse_date(response.headers.get("Last-Modified")),
            parse_result=parse_result,
            keywords=keywords,
            extracted_text=self._extract_text(
                feed,
                categories,
                keywords,
            ),
            **attrs.asdict(
                feed,
                filter=attrs.filters.exclude(  # type: ignore
                    self._feed_attrs.categories,
                    self._feed_attrs.complete,
                    self._feed_attrs.items,
                ),
            ),
        )

        self._podcast.categories.set(categories)

        self._handle_episode_updates(feed)

        return True

    def _extract_text(self, feed: Feed, categories: list[Category], keywords: str) -> str:
        text = " ".join(
            value
            for value in [
                feed.title,
                feed.description,
                feed.owner,
                keywords,
            ]
            + [c.name for c in categories]
            + [item.title for item in feed.items][:6]
            if value
        )
        return " ".join(tokenize(self._podcast.language, text))

    def _handle_failure(self, exc: Exception) -> bool:
        match exc:
            case NotModified():
                active = True
                parse_result = Podcast.ParseResult.NOT_MODIFIED
            case DuplicateFeed():
                active = False
                parse_result = Podcast.ParseResult.DUPLICATE_FEED
            case RssParserError():
                active = False
                parse_result = Podcast.ParseResult.RSS_PARSER_ERROR
            case requests.RequestException():
                active = False
                parse_result = Podcast.ParseResult.HTTP_ERROR
            case _:
                raise

        try:
            http_status = exc.response.status_code  # type: ignore
        except AttributeError:
            http_status = None

        self._save_podcast(
            active=active,
            http_status=http_status,
            parse_result=parse_result,
        )
        return False

    def _save_podcast(self, **fields) -> None:
        now = timezone.now()
        Podcast.objects.filter(pk=self._podcast.id).update(
            updated=now,
            parsed=now,
            **fields,
        )

    def _handle_episode_updates(self, feed: Feed, batch_size: int = 100) -> None:
        qs = Episode.objects.filter(podcast=self._podcast)

        # remove any episodes that may have been deleted on the podcast
        qs.exclude(guid__in={item.guid for item in feed.items}).delete()

        # determine new/current items based on presence of guid

        guids = dict(qs.values_list("guid", "pk"))

        # update existing content

        for batch in batcher(self._episodes_for_update(feed, guids), batch_size):
            Episode.fast_update_objects.fast_update(
                batch,
                fields=[
                    "cover_url",
                    "description",
                    "duration",
                    "episode",
                    "episode_type",
                    "explicit",
                    "keywords",
                    "length",
                    "media_type",
                    "media_url",
                    "pub_date",
                    "season",
                    "title",
                ],
            )

        # add new episodes

        for batch in batcher(self._episodes_for_insert(feed, guids), batch_size):
            Episode.objects.bulk_create(batch, ignore_conflicts=True)

    def _episodes_for_update(self, feed: Feed, guids: dict[str, int]) -> Generator[Episode, None, None]:

        episode_ids = set()

        for item in (item for item in feed.items if item.guid in guids):
            if (episode_id := guids[item.guid]) not in episode_ids:
                yield self._make_episode(item, episode_id)
                episode_ids.add(episode_id)

    def _episodes_for_insert(self, feed: Feed, guids: dict[str, int]) -> Generator[Episode, None, None]:
        return (self._make_episode(item) for item in feed.items if item.guid not in guids)

    def _make_episode(self, item: Item, episode_id: int | None = None) -> Episode:
        return Episode(
            pk=episode_id,
            podcast=self._podcast,
            **attrs.asdict(
                item,
                filter=attrs.filters.exclude(  # type: ignore
                    self._item_attrs.categories,
                ),
            ),
        )
