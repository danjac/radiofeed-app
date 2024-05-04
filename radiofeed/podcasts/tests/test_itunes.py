import http
import pathlib

import httpx
import pytest

from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory

MOCK_RESULT = {
    "feedUrl": "https://feeds.fireside.fm/testandcode/rss",
    "collectionName": "Test & Code : Python Testing",
    "collectionViewUrl": "https//itunes.com/id123345",
    "artworkUrl600": "https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
}


def _mock_page(mock_file):
    return (pathlib.Path(__file__).parent / "mocks" / mock_file).read_bytes()


class TestSearch:
    @pytest.fixture()
    def good_client(self):
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    http.HTTPStatus.OK,
                    json={"results": [MOCK_RESULT]},
                )
            )
        )

    @pytest.fixture()
    def invalid_client(self):
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    http.HTTPStatus.OK,
                    json={
                        "results": [
                            {
                                "id": 12345,
                                "url": "bad-url",
                            }
                        ]
                    },
                )
            )
        )

    @pytest.fixture()
    def bad_client(self):
        def _handle(request):
            raise httpx.HTTPError("fail")

        return httpx.Client(transport=httpx.MockTransport(_handle))

    @pytest.mark.django_db()
    def test_not_ok(self, bad_client):
        with pytest.raises(httpx.HTTPError):
            list(itunes.search(bad_client, "test"))
        assert not Podcast.objects.exists()

    @pytest.mark.django_db()
    def test_ok(self, good_client):
        feeds = list(itunes.search(good_client, "test"))
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()

    @pytest.mark.django_db()
    def test_bad_data(self, invalid_client):
        feeds = list(itunes.search(invalid_client, "test"))
        assert not feeds

    @pytest.mark.django_db()
    def test_podcast_exists(self, good_client):
        PodcastFactory(rss="https://feeds.fireside.fm/testandcode/rss")

        feeds = list(itunes.search(good_client, "test"))
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()
