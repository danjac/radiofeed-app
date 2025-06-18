import http

import httpx
import pytest

from radiofeed.http_client import Client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory

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


MOCK_CHART_RESULT = {
    "feed": {
        "title": "Top Shows",
        "id": "https://rss.applemarketingtools.com/api/v2/us/podcasts/top/10/podcasts.json",
        "author": {"name": "Apple", "url": "https://www.apple.com/"},
        "links": [
            {
                "self": "https://rss.applemarketingtools.com/api/v2/us/podcasts/top/10/podcasts.json"
            }
        ],
        "copyright": "Copyright © 2025 Apple Inc. All rights reserved.",
        "country": "us",
        "icon": "https://www.apple.com/favicon.ico",
        "updated": "Wed, 15 Jan 2025 11:56:12 +0000",
        "results": [
            {
                "artistName": "Joe Rogan",
                "id": "360084272",
                "name": "The Joe Rogan Experience",
                "kind": "podcasts",
                "contentAdvisoryRating": "Explict",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Podcasts221/v4/89/4f/94/894f94f2-3d6a-e34d-ec4f-1c6dbf239511/mza_10409584512842304695.jpg/100x100bb.png",
                "genres": [
                    {
                        "genreId": "1303",
                        "name": "Comedy",
                        "url": "https://itunes.apple.com/us/genre/id1303",
                    }
                ],
                "url": "https://podcasts.apple.com/us/podcast/the-joe-rogan-experience/id360084272",
            },
            {
                "artistName": "Mel Robbins",
                "id": "1646101002",
                "name": "The Mel Robbins Podcast",
                "kind": "podcasts",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Podcasts211/v4/5e/48/90/5e4890ce-82ca-1a78-e496-65d65f80855a/mza_12972697874253971245.jpg/100x100bb.png",
                "genres": [
                    {
                        "genreId": "1304",
                        "name": "Education",
                        "url": "https://itunes.apple.com/us/genre/id1304",
                    },
                    {
                        "genreId": "1512",
                        "name": "Health & Fitness",
                        "url": "https://itunes.apple.com/us/genre/id1512",
                    },
                ],
                "url": "https://podcasts.apple.com/us/podcast/the-mel-robbins-podcast/id1646101002",
            },
            {
                "artistName": "The New York Times",
                "id": "1200361736",
                "name": "The Daily",
                "kind": "podcasts",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Podcasts211/v4/c8/1a/71/c81a716b-b5d1-61b7-7d3e-0253a56e63d5/mza_15186388159121451528.jpg/100x100bb.png",
                "genres": [
                    {
                        "genreId": "1489",
                        "name": "News",
                        "url": "https://itunes.apple.com/us/genre/id1489",
                    }
                ],
                "url": "https://podcasts.apple.com/us/podcast/the-daily/id1200361736",
            },
            {
                "artistName": "Ky Dickens",
                "id": "1766382649",
                "name": "The Telepathy Tapes",
                "kind": "podcasts",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Podcasts221/v4/38/33/a6/3833a68b-e6f9-7008-2e2f-5a050dc08f16/mza_17519369644977508722.jpeg/100x100bb.png",
                "genres": [
                    {
                        "genreId": "1324",
                        "name": "Society & Culture",
                        "url": "https://itunes.apple.com/us/genre/id1324",
                    },
                    {
                        "genreId": "1533",
                        "name": "Science",
                        "url": "https://itunes.apple.com/us/genre/id1533",
                    },
                ],
                "url": "https://podcasts.apple.com/us/podcast/the-telepathy-tapes/id1766382649",
            },
            {
                "artistName": "iHeartPodcasts and Tenderfoot TV",
                "id": "1785026094",
                "name": "Monster: BTK",
                "kind": "podcasts",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Podcasts221/v4/2c/bd/8c/2cbd8c6b-5001-ba8e-b696-bc78fbd054be/mza_200878276356084675.jpg/100x100bb.png",
                "genres": [
                    {
                        "genreId": "1488",
                        "name": "True Crime",
                        "url": "https://itunes.apple.com/us/genre/id1488",
                    }
                ],
                "url": "https://podcasts.apple.com/us/podcast/monster-btk/id1785026094",
            },
            {
                "artistName": "audiochuck",
                "id": "1322200189",
                "name": "Crime Junkie",
                "kind": "podcasts",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Podcasts126/v4/8c/35/04/8c350430-2fbf-98d0-0a25-00b76550ffeb/mza_13445204151221888086.jpg/100x100bb.png",
                "genres": [
                    {
                        "genreId": "1488",
                        "name": "True Crime",
                        "url": "https://itunes.apple.com/us/genre/id1488",
                    }
                ],
                "url": "https://podcasts.apple.com/us/podcast/crime-junkie/id1322200189",
            },
            {
                "artistName": "Ascension",
                "id": "1776236328",
                "name": "The Rosary in a Year (with Fr. Mark-Mary Ames)",
                "kind": "podcasts",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Podcasts211/v4/25/0d/52/250d52c0-94a2-f1a1-2f52-0b62ba6f758f/mza_9502207411546595267.jpg/100x100bb.png",
                "genres": [
                    {
                        "genreId": "1314",
                        "name": "Religion & Spirituality",
                        "url": "https://itunes.apple.com/us/genre/id1314",
                    }
                ],
                "url": "https://podcasts.apple.com/us/podcast/the-rosary-in-a-year-with-fr-mark-mary-ames/id1776236328",
            },
            {
                "artistName": "Shawn Ryan",
                "id": "1492492083",
                "name": "Shawn Ryan Show",
                "kind": "podcasts",
                "contentAdvisoryRating": "Explict",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Podcasts112/v4/d0/b3/2d/d0b32d7f-ab2d-5791-83b0-854f698a9184/mza_13561258173056659752.jpg/100x100bb.png",
                "genres": [
                    {
                        "genreId": "1324",
                        "name": "Society & Culture",
                        "url": "https://itunes.apple.com/us/genre/id1324",
                    }
                ],
                "url": "https://podcasts.apple.com/us/podcast/shawn-ryan-show/id1492492083",
            },
            {
                "artistName": "NBC News",
                "id": "1464919521",
                "name": "Dateline NBC",
                "kind": "podcasts",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Podcasts115/v4/8c/00/7a/8c007a42-e550-0214-d4cb-b59cd7edf194/mza_5305664083935674472.jpeg/100x100bb.png",
                "genres": [
                    {
                        "genreId": "1488",
                        "name": "True Crime",
                        "url": "https://itunes.apple.com/us/genre/id1488",
                    },
                    {
                        "genreId": "1489",
                        "name": "News",
                        "url": "https://itunes.apple.com/us/genre/id1489",
                    },
                ],
                "url": "https://podcasts.apple.com/us/podcast/dateline-nbc/id1464919521",
            },
            {
                "artistName": "Audacy, Red Hour, Great Scott",
                "id": "1788381175",
                "name": "The Severance Podcast with Ben Stiller & Adam Scott",
                "kind": "podcasts",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Podcasts221/v4/25/12/93/25129377-ee37-f8ba-1517-33932bb26974/mza_6733938421555330646.jpg/100x100bb.png",
                "genres": [
                    {
                        "genreId": "1309",
                        "name": "TV & Film",
                        "url": "https://itunes.apple.com/us/genre/id1309",
                    }
                ],
                "url": "https://podcasts.apple.com/us/podcast/the-severance-podcast-with-ben-stiller-adam-scott/id1788381175",
            },
        ],
    }
}


class TestItunesFeed:
    def test_str(self):
        assert (
            str(
                itunes.Feed(
                    image="http://example.com/image.jpg",
                    rss="https://feeds.fireside.fm/testandcode/rss",
                    title="Test & Code",
                    url="https://example.com",
                ),
            )
            == "Test & Code"
        )


class TestFetchTopChart:
    @pytest.fixture
    def good_client(self):
        def _get_result(request):
            if request.url.path.endswith("podcasts.json"):
                return httpx.Response(
                    http.HTTPStatus.OK,
                    json=MOCK_CHART_RESULT,
                )
            return httpx.Response(http.HTTPStatus.OK, json=MOCK_SEARCH_RESULT)

        return Client(
            transport=httpx.MockTransport(_get_result),
        )

    @pytest.fixture
    def bad_client(self):
        def _handle(_):
            raise httpx.HTTPError("fail")

        return Client(transport=httpx.MockTransport(_handle))

    @pytest.fixture
    def empty_result_client(self):
        def _handle(_):
            return httpx.Response(http.HTTPStatus.OK, json={})

        return Client(transport=httpx.MockTransport(_handle))

    @pytest.fixture
    def bad_result_client(self):
        def _get_result(request):
            if request.url.path.endswith("podcasts.json"):
                return httpx.Response(
                    http.HTTPStatus.OK,
                    json=MOCK_CHART_RESULT,
                )
            return httpx.Response(http.HTTPStatus.NOT_FOUND)

        return Client(
            transport=httpx.MockTransport(_get_result),
        )

    @pytest.mark.django_db
    def test_get_top_chart(self, good_client):
        feeds = itunes.fetch_chart(good_client, country="us", limit=10)
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss, promoted=True).exists()

    @pytest.mark.django_db
    def test_already_exists(self, good_client):
        podcast = PodcastFactory(
            rss=MOCK_SEARCH_RESULT["results"][0]["feedUrl"],
        )
        feeds = itunes.fetch_chart(good_client, country="us", limit=10)
        assert len(feeds) == 1

        podcast.refresh_from_db()

    @pytest.mark.django_db
    def test_canonical_already_exists(self, good_client):
        podcast = PodcastFactory()
        PodcastFactory(
            canonical=podcast,
            rss=MOCK_SEARCH_RESULT["results"][0]["feedUrl"],
        )
        feeds = itunes.fetch_chart(good_client, country="us", limit=10)
        assert len(feeds) == 1

    @pytest.mark.django_db
    def test_demote(self, good_client):
        podcast = PodcastFactory(rss=MOCK_SEARCH_RESULT["results"][0]["feedUrl"])

        PodcastFactory()
        feeds = itunes.fetch_chart(good_client, country="us", limit=10)

        assert len(feeds) == 1
        assert feeds[0].rss == podcast.rss

    @pytest.mark.django_db
    def test_bad_client(self, bad_client):
        with pytest.raises(itunes.ItunesError):
            itunes.fetch_chart(bad_client, country="us", limit=10)
        assert not Podcast.objects.exists()

    @pytest.mark.django_db
    def test_bad_result(self, bad_result_client):
        with pytest.raises(itunes.ItunesError):
            itunes.fetch_chart(bad_result_client, country="us", limit=10)
        assert not Podcast.objects.exists()

    @pytest.mark.django_db
    def test_empty_result(self, empty_result_client):
        itunes.fetch_chart(empty_result_client, country="us", limit=10)
        assert not Podcast.objects.exists()


class TestSearch:
    @pytest.fixture
    def good_client(self):
        return Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    http.HTTPStatus.OK,
                    json=MOCK_SEARCH_RESULT,
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
        feeds = itunes.search(good_client, "test")
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()

    @pytest.mark.django_db
    def test_not_ok(self, bad_client):
        with pytest.raises(itunes.ItunesError):
            itunes.search(bad_client, "test")
        assert not Podcast.objects.exists()

    @pytest.mark.django_db
    def test_bad_data(self, invalid_client):
        feeds = itunes.search(invalid_client, "test")
        assert len(feeds) == 0
        assert feeds == []

    @pytest.mark.django_db
    def test_podcast_exists(self, good_client):
        PodcastFactory(rss="https://feeds.fireside.fm/testandcode/rss")

        feeds = list(itunes.search(good_client, "test"))
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()

    @pytest.mark.django_db
    def test_cached(self, mocker, _locmem_cache):
        client = Client()
        mock_search = mocker.patch(
            "radiofeed.podcasts.itunes.search",
            return_value=MOCK_SEARCH_RESULT,
        )
        itunes.search_cached(client, "test")
        itunes.search_cached(client, "test")
        mock_search.assert_called_once()
