import http
import pathlib

import httpx
import pytest

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
    @pytest.fixture
    def good_client(self):
        def _get_result(request):
            if "podcasts.apple.com" in str(request.url):
                with (
                    pathlib.Path(__file__).parent / "mocks" / "itunes_chart.html"
                ).open("rb") as f:
                    chart_content = f.read()

                return httpx.Response(
                    http.HTTPStatus.OK,
                    content=chart_content,
                )
            return httpx.Response(http.HTTPStatus.OK, json=MOCK_SEARCH_RESULT)

        return Client(
            transport=httpx.MockTransport(_get_result),
        )

    @pytest.mark.django_db
    def test_ok(self, good_client):
        feeds = list(itunes.fetch_top_feeds(good_client, country="us"))
        assert len(feeds) == 1

    @pytest.mark.django_db
    def test_get_genre(self, good_client):
        feeds = list(itunes.fetch_top_feeds(good_client, country="us", genre_id=1303))
        assert len(feeds) == 1

    @pytest.mark.django_db
    def test_fail(self):
        def _handle(_):
            raise httpx.HTTPError("fail")

        client = Client(transport=httpx.MockTransport(_handle))

        with pytest.raises(itunes.ItunesError):
            list(itunes.fetch_top_feeds(client, country="us"))

    @pytest.mark.django_db
    def test_empty(self):
        def _handle(_):
            return httpx.Response(
                http.HTTPStatus.OK,
                content=b"",
            )

        client = Client(transport=httpx.MockTransport(_handle))

        with pytest.raises(itunes.ItunesError):
            list(itunes.fetch_top_feeds(client, country="us"))


class TestSaveFeedsToDB:
    @pytest.mark.django_db
    def test_save_feeds_to_db(self):
        feeds = [
            itunes.Feed(
                artworkUrl100="http://example.com/image.jpg",
                collectionName="Test & Code",
                collectionViewUrl="https://example.com",
                feedUrl="https://feeds.fireside.fm/testandcode/rss",
            )
        ]
        itunes.save_feeds_to_db(feeds)

        assert Podcast.objects.filter(
            rss="https://feeds.fireside.fm/testandcode/rss"
        ).exists()

    @pytest.mark.django_db
    def test_save_with_extra_fields(self):
        feeds = [
            itunes.Feed(
                artworkUrl100="http://example.com/image.jpg",
                collectionName="Test & Code",
                collectionViewUrl="https://example.com",
                feedUrl="https://feeds.fireside.fm/testandcode/rss",
            )
        ]
        itunes.save_feeds_to_db(feeds, promoted=True)

        podcast = Podcast.objects.get(rss="https://feeds.fireside.fm/testandcode/rss")
        assert podcast.promoted is True


class TestSearch:
    @pytest.mark.django_db
    def test_ok(self):
        client = Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    http.HTTPStatus.OK,
                    json=MOCK_SEARCH_RESULT,
                )
            ),
        )
        feeds = itunes.search(client, "test", limit=30)
        assert len(feeds) == 1

    @pytest.mark.django_db
    def test_http_error(self):
        def _handle(_):
            raise httpx.HTTPError("fail")

        client = Client(transport=httpx.MockTransport(_handle))

        with pytest.raises(itunes.ItunesError):
            itunes.search(client, "test", limit=30)

    @pytest.mark.django_db
    def test_bad_data(self):
        client = Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    http.HTTPStatus.OK,
                    json={
                        "results": [
                            {
                                "id": 12345,
                                "url": "bad-url",
                            }
                        ],
                    },
                )
            ),
        )

        feeds = itunes.search(client, "test", limit=30)
        assert len(feeds) == 0
        assert feeds == []

    @pytest.mark.django_db
    def test_not_json(self):
        client = Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    http.HTTPStatus.OK,
                    content=b"not json",
                )
            ),
        )
        with pytest.raises(itunes.ItunesError):
            itunes.search(client, "test", limit=30)


class TestSearchCached:
    @pytest.mark.django_db
    def test_cached(self, mocker, _locmem_cache):
        client = Client()
        mock_search = mocker.patch(
            "radiofeed.podcasts.itunes.search",
            return_value=MOCK_SEARCH_RESULT,
        )
        feeds, is_new = itunes.search_cached(client, "test", limit=30)
        assert is_new is True
        assert len(feeds) == 2

        feeds, is_new = itunes.search_cached(client, "test", limit=30)
        assert is_new is False
        assert len(feeds) == 2
        mock_search.assert_called_once()
