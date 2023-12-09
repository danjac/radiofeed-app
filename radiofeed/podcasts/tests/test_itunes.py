import http
import pathlib

import httpx
import pytest
from django.core.cache import cache

from radiofeed.podcasts import itunes
from radiofeed.podcasts.itunes import CatalogParser
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import create_podcast

MOCK_RESULT = {
    "feedUrl": "https://feeds.fireside.fm/testandcode/rss",
    "collectionName": "Test & Code : Python Testing",
    "collectionViewUrl": "https//itunes.com/id123345",
    "artworkUrl600": "https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
}


def _mock_page(mock_file):
    return (pathlib.Path(__file__).parent / "mocks" / mock_file).read_bytes()


class TestCatalogParser:
    @pytest.mark.django_db()
    def test_parse(self):
        list(CatalogParser(locale="us").parse(self._get_client()))

        assert Podcast.objects.count() == 1

    @pytest.mark.django_db()
    def test_parse_with_category_error(self):
        list(CatalogParser(locale="us").parse(self._get_client(category_ok=False)))
        assert Podcast.objects.count() == 0

    @pytest.mark.django_db()
    def test_parse_with_genre_error(self):
        list(CatalogParser(locale="us").parse(self._get_client(genre_ok=False)))
        assert Podcast.objects.count() == 0

    @pytest.mark.django_db()
    def test_parse_with_api_lookup_error(self):
        list(CatalogParser(locale="us").parse(self._get_client(json_ok=False)))
        assert Podcast.objects.count() == 0

    def _get_client(self, *, json_ok=True, category_ok=True, genre_ok=True):
        def _handler(request):
            match request.url.path.split("/"):
                case [*_, "lookup"]:
                    if json_ok:
                        return httpx.Response(
                            http.HTTPStatus.OK, json={"results": [MOCK_RESULT]}
                        )
                    raise httpx.HTTPError("could not do lookup")

                case [*_, "genre", "podcasts", "id26"]:
                    if category_ok:
                        return httpx.Response(
                            http.HTTPStatus.OK, content=_mock_page("podcasts.html")
                        )
                    raise httpx.HTTPError("could not parse podcasts page")

                case [*_, "genre", _, _]:
                    if genre_ok:
                        return httpx.Response(
                            http.HTTPStatus.OK, content=_mock_page("genre.html")
                        )
                    raise httpx.HTTPError("could not parse genre page")

                case _:
                    return httpx.Response(http.HTTPStatus.OK)

        return httpx.Client(transport=httpx.MockTransport(_handler))


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
    @pytest.mark.usefixtures("_locmem_cache")
    def test_is_not_cached(self, good_client):
        feeds = itunes.search(good_client, "test")

        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()

        assert cache.get(itunes.search_cache_key("test")) == feeds

    @pytest.mark.django_db()
    @pytest.mark.usefixtures("_locmem_cache")
    def test_is_cached(self, good_client):
        cache.set(
            itunes.search_cache_key("test"),
            [
                itunes.Feed(
                    rss="https://example.com",
                    title="test",
                    url="https://example.com/id1234",
                )
            ],
        )

        feeds = itunes.search(good_client, "test")

        assert len(feeds) == 1
        assert not Podcast.objects.filter(rss=feeds[0].url).exists()

    @pytest.mark.django_db()
    def test_podcast_exists(self, good_client):
        create_podcast(rss="https://feeds.fireside.fm/testandcode/rss")

        feeds = list(itunes.search(good_client, "test"))
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()
