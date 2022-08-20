from __future__ import annotations

import http

from typing import Iterator

import attrs
import requests

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.http import http_date, quote_etag

from radiofeed.crypto import make_content_hash
from radiofeed.feedparser.date_parser import parse_date
from radiofeed.batcher import batcher
from radiofeed.tokenizer import tokenize
from radiofeed.episodes.models import Episode
from radiofeed.feedparser import rss_parser, scheduler
from radiofeed.feedparser.exceptions import DuplicateFeed, NotModified, RssParserError
from radiofeed.feedparser.models import Feed, Item
from radiofeed.podcasts.models import Category, Podcast


def parse_feed(podcast: Podcast) -> bool:
    """Parse podcast RSS feed."""
    return FeedParser(podcast).parse()


class FeedParser:
    """Updates a Podcast instance with its RSS or Atom feed source."""

    _accept_header: tuple[str, ...] = (
        "application/atom+xml",
        "application/rdf+xml",
        "application/rss+xml",
        "application/x-netcdf",
        "application/xml;q=0.9",
        "text/xml;q=0.2",
        "*/*;q=0.1",
    )

    _max_retries: int = 3

    def __init__(self, podcast: Podcast):
        self._podcast = podcast

        self._feed_attrs = attrs.fields(Feed)
        self._item_attrs = attrs.fields(Item)

    @transaction.atomic
    def parse(self) -> bool:
        """Updates Podcast instance with RSS or Atom feed source.

        Podcast details are updated and episodes created, updated or deleted accordingly.

        If a podcast is discontinued (e.g. there is a duplicate feed in the database, or the feed is marked as complete) then the podcast is set inactive.

        Returns:
            True if podcast has been successfully updated.
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

        # Check if not modified: feed should return a 304 if no new updates,
        # but not in all cases, so we should also check the content body.
        if (
            response.status_code == http.HTTPStatus.NOT_MODIFIED
            or (content_hash := make_content_hash(response.content))
            == self._podcast.content_hash
        ):
            raise NotModified(response=response)

        # Check if there is another active feed with the same URL/content
        if (
            Podcast.objects.exclude(pk=self._podcast.id).filter(
                Q(content_hash=content_hash) | Q(rss=response.url)
            )
        ).exists():
            raise DuplicateFeed(response=response)

        return response, rss_parser.parse_rss(response.content), content_hash

    def _get_feed_headers(self) -> dict:
        headers = {
            "Accept": ",".join(self._accept_header),
            "User-Agent": settings.USER_AGENT,
        }

        if self._podcast.etag:
            headers["If-None-Match"] = quote_etag(self._podcast.etag)
        if self._podcast.modified:
            headers["If-Modified-Since"] = http_date(self._podcast.modified.timestamp())
        return headers

    def _handle_success(
        self,
        response: requests.Response,
        feed: Feed,
        content_hash: str,
    ) -> bool:

        if feed.complete:
            active = False
            parse_result = Podcast.ParseResult.COMPLETE
        else:
            active = True
            parse_result = Podcast.ParseResult.SUCCESS

        category_names = {c.casefold() for c in feed.categories}

        categories = Category.objects.annotate(lowercase_name=Lower("name")).filter(
            lowercase_name__in=category_names
        )

        self._save_podcast(
            active=active,
            parse_result=parse_result,
            num_retries=0,
            content_hash=content_hash,
            rss=response.url,
            etag=response.headers.get("ETag", ""),
            http_status=response.status_code,
            modified=parse_date(response.headers.get("Last-Modified")),
            extracted_text=self._extract_text(feed),
            keywords=" ".join(category_names - {c.lowercase_name for c in categories}),
            frequency=scheduler.schedule(feed),
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
        self._episode_updates(feed)

        return True

    def _handle_failure(self, exc: Exception) -> bool:
        try:
            http_status = exc.response.status_code  # type: ignore
        except AttributeError:
            http_status = None

        num_retries: int = self._podcast.num_retries
        active: bool = True

        match exc:
            case NotModified():
                parse_result = Podcast.ParseResult.NOT_MODIFIED
                num_retries = 0
            case DuplicateFeed():
                active = False
                parse_result = Podcast.ParseResult.DUPLICATE_FEED
            case RssParserError():
                parse_result = Podcast.ParseResult.RSS_PARSER_ERROR
                num_retries += 1
            case requests.RequestException():
                parse_result = (
                    Podcast.ParseResult.COMPLETE
                    if http_status == http.HTTPStatus.GONE
                    else Podcast.ParseResult.HTTP_ERROR
                )

                active = http_status not in (
                    http.HTTPStatus.FORBIDDEN,
                    http.HTTPStatus.NOT_FOUND,
                    http.HTTPStatus.GONE,
                    http.HTTPStatus.UNAUTHORIZED,
                )

                num_retries += 1

            case _:
                raise

        self._save_podcast(
            active=active and num_retries < self._max_retries,
            http_status=http_status,
            parse_result=parse_result,
            num_retries=num_retries,
            frequency=scheduler.reschedule(
                self._podcast.pub_date,
                self._podcast.frequency,
            ),
        )
        return False

    def _save_podcast(self, **fields) -> None:
        now = timezone.now()
        Podcast.objects.filter(pk=self._podcast.id).update(
            updated=now,
            parsed=now,
            **fields,
        )

    def _extract_text(self, feed: Feed) -> str:
        text = " ".join(
            value
            for value in [
                feed.title,
                feed.description,
                feed.owner,
            ]
            + feed.categories
            + [item.title for item in feed.items][:6]
            if value
        )
        return " ".join(tokenize(self._podcast.language, text))

    def _episode_updates(self, feed: Feed) -> None:
        qs = Episode.objects.filter(podcast=self._podcast)

        # remove any episodes that may have been deleted on the podcast
        qs.exclude(guid__in={item.guid for item in feed.items}).delete()

        # determine new/current items based on presence of guid

        guids = dict(qs.values_list("guid", "pk"))

        # update existing content

        for batch in batcher(self._episodes_for_update(feed, guids), 1000):
            Episode.fast_update_objects.copy_update(
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

        for batch in batcher(self._episodes_for_insert(feed, guids), 100):
            Episode.objects.bulk_create(batch, ignore_conflicts=True)

    def _episodes_for_insert(
        self, feed: Feed, guids: dict[str, int]
    ) -> Iterator[Episode]:
        return (
            self._make_episode(item) for item in feed.items if item.guid not in guids
        )

    def _episodes_for_update(
        self, feed: Feed, guids: dict[str, int]
    ) -> Iterator[Episode]:

        episode_ids = set()

        for item in (item for item in feed.items if item.guid in guids):
            if (episode_id := guids[item.guid]) not in episode_ids:
                yield self._make_episode(item, episode_id)
                episode_ids.add(episode_id)

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
