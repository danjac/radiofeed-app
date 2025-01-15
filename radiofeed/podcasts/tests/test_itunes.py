import http

import httpx
import pytest

from radiofeed.http_client import Client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory

MOCK_RESULT = {
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


class TestSearch:
    @pytest.fixture
    def good_client(self):
        return Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    http.HTTPStatus.OK,
                    json=MOCK_RESULT,
                )
            ),
        )

    @pytest.fixture
    def invalid_client(self):
        return Client(
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

    @pytest.fixture
    def bad_client(self):
        def _handle(_):
            raise httpx.HTTPError("fail")

        return Client(transport=httpx.MockTransport(_handle))

    @pytest.mark.django_db
    def test_ok(self, good_client):
        feeds = list(itunes.search(good_client, "test"))
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()

    @pytest.mark.django_db
    def test_not_ok(self, bad_client):
        feeds = list(itunes.search(bad_client, "test"))
        assert len(feeds) == 0
        assert not Podcast.objects.exists()

    @pytest.mark.django_db
    def test_bad_data(self, invalid_client):
        feeds = list(itunes.search(invalid_client, "test"))
        assert len(feeds) == 0
        assert feeds == []

    @pytest.mark.django_db
    @pytest.mark.usefixtures("_locmem_cache")
    def test_is_not_cached(self, good_client):
        feeds = list(itunes.search(good_client, "test"))

        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()

    @pytest.mark.django_db
    def test_podcast_exists(self, good_client):
        PodcastFactory(rss="https://feeds.fireside.fm/testandcode/rss")

        feeds = list(itunes.search(good_client, "test"))
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()
