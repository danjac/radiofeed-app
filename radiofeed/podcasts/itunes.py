import contextlib
import dataclasses
import itertools
from collections.abc import Iterator

import httpx

from radiofeed.http_client import Client
from radiofeed.podcasts.models import Podcast


@dataclasses.dataclass(frozen=True)
class Feed:
    """Encapsulates iTunes API result.

    Attributes:
        rss: URL to RSS or Atom resource
        url: URL to website of podcast
        title: title of podcast
        image: URL to cover image
        podcast: matching Podcast instance in local database
    """

    rss: str
    url: str
    title: str = ""
    image: str = ""
    podcast: Podcast | None = None

    def __str__(self) -> str:
        """Returns title or RSS URL."""
        return self.title or self.rss


def search(
    client: Client,
    search_term: str,
    *,
    limit: int = 50,
) -> Iterator[Feed]:
    """Search iTunes podcast API."""
    return _ItunesClient(client).search(search_term, limit=limit)


def fetch_chart(
    client: Client,
    *,
    location: str,
    limit: int = 50,
) -> Iterator[Feed]:
    """Fetch top chart from iTunes podcast API.
    New or updated podcasts are inserted or updated with `promoted=True`.
    """
    return _ItunesClient(client).fetch_chart(location=location, limit=limit)


@dataclasses.dataclass(frozen=True)
class _ItunesClient:
    client: Client

    def search(self, search_term: str, *, limit: int = 50) -> Iterator[Feed]:
        """Search iTunes podcast API."""
        feeds_for_podcasts, feeds = itertools.tee(
            self._fetch_search_feeds(search_term, limit)
        )

        podcasts = Podcast.objects.filter(
            rss__in={f.rss for f in feeds_for_podcasts}
        ).in_bulk(field_name="rss")

        # insert podcasts to feeds where we have a match

        feeds_for_insert, feeds = itertools.tee(
            [
                dataclasses.replace(feed, podcast=podcasts.get(feed.rss))
                for feed in feeds
            ],
        )

        # create new podcasts for feeds without a match

        Podcast.objects.bulk_create(
            [
                Podcast(title=feed.title, rss=feed.rss)
                for feed in set(feeds_for_insert)
                if feed.podcast is None
            ],
            ignore_conflicts=True,
        )

        return feeds

    def fetch_chart(
        self,
        *,
        location: str = "us",
        limit: int = 50,
    ) -> Iterator[Feed]:
        feeds_for_podcasts, feeds = itertools.tee(
            self._fetch_chart_feeds(location, limit)
        )

        Podcast.objects.bulk_create(
            [
                Podcast(
                    rss=feed.rss,
                    promoted=True,
                )
                for feed in feeds_for_podcasts
            ],
            unique_fields=["rss"],
            update_fields=["promoted"],
            update_conflicts=True,
        )

        return feeds

    def _fetch_search_feeds(
        self,
        search_term: str,
        limit: int,
    ) -> Iterator[Feed]:
        return self._fetch_feeds(
            "https://itunes.apple.com/search",
            term=search_term,
            limit=limit,
            media="podcast",
        )

    def _fetch_chart_feeds(self, location: str, limit: int) -> Iterator[Feed]:
        if itunes_ids := set(self._fetch_chart_ids(location, limit)):
            return self._fetch_feeds(
                "https://itunes.apple.com/lookup",
                id=",".join(itunes_ids),
            )
        return iter(())

    def _fetch_chart_ids(self, location: str, limit: int) -> Iterator[str]:
        for result in (
            self._fetch_json(
                f"https://rss.marketingtools.apple.com/api/v2/{location}/podcasts/top/{limit}/podcasts.json"
            )
            .get("feed", {})
            .get("results", [])
        ):
            if itunes_id := result.get("id", None):
                yield itunes_id

    def _fetch_json(self, url: str, **params) -> dict:
        with contextlib.suppress(httpx.HTTPError):
            response = self.client.get(
                url,
                params=params,
                headers={"Accept": "application/json"},
            )
            return response.json()
        return {}

    def _fetch_feeds(self, url: str, **params) -> Iterator[Feed]:
        return self._parse_feeds(self._fetch_json(url, **params).get("results", []))

    def _parse_feeds(self, source: list[dict]) -> Iterator[Feed]:
        # ensure unique feeds
        feed_urls: set[str] = set()

        for result in source:
            if (feed := self._parse_feed(result)) and feed.rss not in feed_urls:
                feed_urls.add(feed.rss)
                yield feed

    def _parse_feed(self, feed: dict) -> Feed | None:
        with contextlib.suppress(KeyError):
            return Feed(
                rss=feed["feedUrl"],
                url=feed["collectionViewUrl"],
                title=feed["collectionName"],
                image=feed["artworkUrl100"],
            )
        return None
