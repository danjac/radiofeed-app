import functools
import hashlib
import http
from collections.abc import Iterator

import attrs
import httpx
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Lower
from django.db.utils import DataError
from django.utils import timezone
from django.utils.http import http_date, quote_etag

from radiofeed import batcher, tokenizer
from radiofeed.episodes.models import Episode
from radiofeed.feedparser import rss_parser, scheduler
from radiofeed.feedparser.date_parser import parse_date
from radiofeed.feedparser.exceptions import (
    DuplicateError,
    FeedParserError,
    InaccessibleError,
    InvalidDataError,
    InvalidRSSError,
    NotModifiedError,
    UnavailableError,
)
from radiofeed.feedparser.models import Feed, Item
from radiofeed.podcasts.models import Category, Podcast


@functools.cache
def get_categories() -> dict[str, Category]:
    """Returns a cached dict of categories with lowercase names as key."""
    return {
        category.lowercase_name: category
        for category in Category.objects.annotate(lowercase_name=Lower("name"))
    }


def make_content_hash(content: bytes) -> str:
    """Hashes RSS content."""
    return hashlib.sha256(content).hexdigest()


class FeedParser:
    """Updates a Podcast instance with its RSS or Atom feed source."""

    _max_retries: int = 3
    _request_timeout: int = 5

    _feed_attrs = attrs.fields(Feed)
    _item_attrs = attrs.fields(Item)

    _accept_header: str = (
        "application/atom+xml,"
        "application/rdf+xml,"
        "application/rss+xml,"
        "application/x-netcdf,"
        "application/xml;q=0.9,"
        "text/xml;q=0.2,"
        "*/*;q=0.1"
    )

    def __init__(self, podcast: Podcast):
        self._podcast = podcast

    @classmethod
    def get_client(cls, **kwargs) -> httpx.Client:
        """Returns Client instance for making requests."""
        return httpx.Client(
            timeout=cls._request_timeout,
            follow_redirects=True,
            **kwargs,
        )

    def parse(self, client: httpx.Client) -> None:
        """Syncs Podcast instance with RSS or Atom feed source.

        Podcast details are updated and episodes created, updated or deleted
        accordingly.

        If any `fields` these will be set on podcast on each update (successful or not).

        Raises:
            FeedParserError: if any errors found in fetching or parsing the feed.
        """
        try:
            response = self._get_response(client)
            content_hash = self._make_content_hash(response)
            self._check_duplicates(response, content_hash)
            self._handle_update(
                response=response,
                content_hash=content_hash,
                feed=rss_parser.parse_rss(response.content),
            )
        except FeedParserError as exc:
            self._handle_error(exc)

    def _make_content_hash(self, response: httpx.Response) -> str:
        content_hash = make_content_hash(response.content)

        # check content hash has changed
        if content_hash == self._podcast.content_hash:
            raise NotModifiedError

        return content_hash

    def _check_duplicates(self, response: httpx.Response, content_hash: str) -> None:
        # check no other podcast with this RSS URL or identical content
        if (
            Podcast.objects.exclude(pk=self._podcast.pk)
            .filter(Q(rss=response.url) | Q(content_hash=content_hash))
            .exists()
        ):
            raise DuplicateError

    def _handle_update(
        self,
        *,
        response: httpx.Response,
        content_hash: str,
        feed: Feed,
    ) -> None:
        categories, keywords = self._parse_taxonomy(feed)

        try:
            with transaction.atomic():
                self._podcast_update(
                    num_retries=0,
                    parser_error=None,
                    content_hash=content_hash,
                    keywords=keywords,
                    rss=response.url,
                    active=not (feed.complete),
                    etag=response.headers.get("ETag", ""),
                    modified=parse_date(response.headers.get("Last-Modified")),
                    extracted_text=self._extract_text(feed),
                    frequency=scheduler.schedule(feed),
                    **attrs.asdict(
                        feed,
                        filter=attrs.filters.exclude(
                            self._feed_attrs.categories,
                            self._feed_attrs.complete,
                            self._feed_attrs.items,
                        ),
                    ),
                )

                self._podcast.categories.set(categories)
                self._episode_updates(feed)
        except DataError as exc:
            raise InvalidDataError from exc

    def _get_response(self, client: httpx.Client) -> httpx.Response:
        try:
            response = client.get(self._podcast.rss, headers=self._get_headers())
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == http.HTTPStatus.NOT_MODIFIED:
                    raise NotModifiedError from exc
                if exc.response.is_client_error:
                    raise InaccessibleError from exc
                raise

            return response
        except httpx.HTTPError as exc:
            raise UnavailableError from exc

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": self._accept_header,
            "User-Agent": settings.USER_AGENT,
        }
        if self._podcast.etag:
            headers["If-None-Match"] = quote_etag(self._podcast.etag)
        if self._podcast.modified:
            headers["If-Modified-Since"] = http_date(self._podcast.modified.timestamp())
        return headers

    def _handle_error(self, exc: FeedParserError) -> None:
        num_retries: int = self._podcast.num_retries
        active: bool = True

        match exc:
            case DuplicateError() | InaccessibleError():
                # podcast should be discontinued and no longer updated
                active = False

            case InvalidDataError() | InvalidRSSError() | UnavailableError():
                # increment num_retries in case a temporary error
                num_retries += 1

            case _:
                # any other result: reset num_retries
                num_retries = 0

        # if number of errors exceeds threshold then deactivate the podcast
        active = active and num_retries < self._max_retries

        # if podcast is still active, reschedule next update check
        frequency = (
            scheduler.reschedule(
                self._podcast.pub_date,
                self._podcast.frequency,
            )
            if active
            else self._podcast.frequency
        )

        self._podcast_update(
            active=active,
            num_retries=num_retries,
            frequency=frequency,
            parser_error=exc.parser_error,
        )

        # re-raise original exception
        raise exc

    def _podcast_update(self, **fields) -> None:
        now = timezone.now()

        Podcast.objects.filter(pk=self._podcast.pk).update(
            updated=now,
            parsed=now,
            **fields,
        )

    def _parse_taxonomy(self, feed: Feed) -> tuple[list[Category], str]:
        categories: list[Category] = []
        keywords: str = ""

        if category_names := {c.casefold() for c in feed.categories}:
            categories_dct = get_categories()

            categories = [
                categories_dct[name]
                for name in category_names
                if name in categories_dct
            ]

            keywords = " ".join(
                [name for name in category_names if name not in categories_dct]
            )

        return categories, keywords

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
        return " ".join(tokenizer.tokenize(self._podcast.language, text))

    def _episode_updates(self, feed: Feed) -> None:
        qs = Episode.objects.filter(podcast=self._podcast)

        # remove any episodes that may have been deleted on the podcast
        qs.exclude(guid__in={item.guid for item in feed.items}).delete()

        # determine new/current items based on presence of guid

        guids = dict(qs.values_list("guid", "pk"))

        # update existing content

        for batch in batcher.batch(self._episodes_for_update(feed, guids), 1000):
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
                    "length",
                    "media_type",
                    "media_url",
                    "pub_date",
                    "season",
                    "title",
                ],
            )

        # add new episodes

        for batch in batcher.batch(self._episodes_for_insert(feed, guids), 100):
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
                filter=attrs.filters.exclude(self._item_attrs.categories),
            ),
        )
