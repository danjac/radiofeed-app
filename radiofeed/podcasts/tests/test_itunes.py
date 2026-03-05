import http
import pathlib
import re

import aiohttp
import pytest
from aioresponses import aioresponses

from radiofeed.client import Client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast

MOCK_SEARCH_RESULT = {
    "results": [
        {
            "feedUrl": "https://feeds.fireside.fm/testandcode/rss",
            "collectionName": "Test & Code : Python Testing",
            "collectionViewUrl": "https//itunes.com/id123345",
            "artworkUrl100": "https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
        }
    ],
    "resultCount": 1,
}


class TestItunesFeed:
    def test_str(self):
        assert (
            str(
                itunes.Feed(
                    artworkUrl100="http://example.com/image.jpg",
                    collectionName="Test & Code",
                    collectionViewUrl="https://example.com",
                    feedUrl="https://feeds.fireside.fm/testandcode/rss",
                ),
            )
            == "Test & Code"
        )


class TestTopFeeds:
    @pytest.mark.django_db
    async def test_ok(self):
        chart_content = (
            pathlib.Path(__file__).parent / "mocks" / "itunes_chart.html"
        ).read_bytes()

        with aioresponses() as m:
            m.get(
                "https://podcasts.apple.com/us/charts",
                status=http.HTTPStatus.OK,
                body=chart_content,
            )
            m.get(
                re.compile(r"https://itunes\.apple\.com/lookup.*"),
                status=http.HTTPStatus.OK,
                payload=MOCK_SEARCH_RESULT,
            )
            client = Client()
            feeds = await itunes.fetch_top_feeds(client, country="us")
            await client.aclose()
        assert len(feeds) == 1

    @pytest.mark.django_db
    async def test_get_genre(self):
        chart_content = (
            pathlib.Path(__file__).parent / "mocks" / "itunes_chart.html"
        ).read_bytes()

        with aioresponses() as m:
            m.get(
                "https://podcasts.apple.com/us/genre/1303",
                status=http.HTTPStatus.OK,
                body=chart_content,
            )
            m.get(
                re.compile(r"https://itunes\.apple\.com/lookup.*"),
                status=http.HTTPStatus.OK,
                payload=MOCK_SEARCH_RESULT,
            )
            client = Client()
            feeds = await itunes.fetch_top_feeds(client, country="us", genre_id=1303)
            await client.aclose()
        assert len(feeds) == 1

    @pytest.mark.django_db
    async def test_fail(self):
        with aioresponses() as m:
            m.get(
                "https://podcasts.apple.com/us/charts",
                exception=aiohttp.ClientError("fail"),
            )
            client = Client()
            with pytest.raises(itunes.ItunesError):
                await itunes.fetch_top_feeds(client, country="us")
            await client.aclose()

    @pytest.mark.django_db
    async def test_empty(self):
        with aioresponses() as m:
            m.get(
                "https://podcasts.apple.com/us/charts",
                status=http.HTTPStatus.OK,
                body=b"",
            )
            client = Client()
            with pytest.raises(itunes.ItunesError):
                await itunes.fetch_top_feeds(client, country="us")
            await client.aclose()


class TestSaveFeedsToDB:
    @pytest.mark.django_db(transaction=True)
    async def test_save_feeds_to_db(self):
        feeds = [
            itunes.Feed(
                artworkUrl100="http://example.com/image.jpg",
                collectionName="Test & Code",
                collectionViewUrl="https://example.com",
                feedUrl="https://feeds.fireside.fm/testandcode/rss",
            )
        ]
        await itunes.save_feeds_to_db(feeds)

        assert Podcast.objects.filter(
            rss="https://feeds.fireside.fm/testandcode/rss"
        ).exists()

    @pytest.mark.django_db(transaction=True)
    async def test_save_with_extra_fields(self):
        feeds = [
            itunes.Feed(
                artworkUrl100="http://example.com/image.jpg",
                collectionName="Test & Code",
                collectionViewUrl="https://example.com",
                feedUrl="https://feeds.fireside.fm/testandcode/rss",
            )
        ]
        await itunes.save_feeds_to_db(feeds, promoted=True)

        podcast = Podcast.objects.get(rss="https://feeds.fireside.fm/testandcode/rss")
        assert podcast.promoted is True


class TestSearch:
    @pytest.mark.django_db
    async def test_ok(self):
        with aioresponses() as m:
            m.get(
                re.compile(r"https://itunes\.apple\.com/search.*"),
                status=http.HTTPStatus.OK,
                payload=MOCK_SEARCH_RESULT,
            )
            client = Client()
            feeds = await itunes.search(client, "test", limit=30)
            await client.aclose()
        assert len(feeds) == 1

    @pytest.mark.django_db
    async def test_http_error(self):
        with aioresponses() as m:
            m.get(
                re.compile(r"https://itunes\.apple\.com/search.*"),
                exception=aiohttp.ClientError("fail"),
            )
            client = Client()
            with pytest.raises(itunes.ItunesError):
                await itunes.search(client, "test", limit=30)
            await client.aclose()

    @pytest.mark.django_db
    async def test_bad_data(self):
        with aioresponses() as m:
            m.get(
                re.compile(r"https://itunes\.apple\.com/search.*"),
                status=http.HTTPStatus.OK,
                payload={"results": [{"id": 12345, "url": "bad-url"}]},
            )
            client = Client()
            feeds = await itunes.search(client, "test", limit=30)
            await client.aclose()
        assert len(feeds) == 0
        assert feeds == []

    @pytest.mark.django_db
    async def test_not_json(self):
        with aioresponses() as m:
            m.get(
                re.compile(r"https://itunes\.apple\.com/search.*"),
                status=http.HTTPStatus.OK,
                body=b"not json",
            )
            client = Client()
            with pytest.raises(itunes.ItunesError):
                await itunes.search(client, "test", limit=30)
            await client.aclose()


class TestSearchCached:
    @pytest.mark.django_db
    async def test_cached(self, mocker, _locmem_cache):
        client = Client()
        mock_search = mocker.patch(
            "radiofeed.podcasts.itunes.search",
            return_value=MOCK_SEARCH_RESULT,
        )
        feeds, is_new = await itunes.search_cached(client, "test", limit=30)
        assert is_new is True
        assert len(feeds) == 2

        feeds, is_new = await itunes.search_cached(client, "test", limit=30)
        assert is_new is False
        assert len(feeds) == 2
        mock_search.assert_called_once()
        await client.aclose()
