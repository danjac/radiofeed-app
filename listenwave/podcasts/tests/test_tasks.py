import pytest

from listenwave.podcasts.itunes import Feed
from listenwave.podcasts.tasks import fetch_itunes_feeds


class TestFetchTopItunes:
    country = "gb"
    itunes_genre_id = 1301

    @pytest.fixture
    def feed(self):
        return Feed(
            artworkUrl100="http://example.com/artwork.jpg",
            collectionName="Example Podcast",
            collectionViewUrl="http://example.com/podcast",
            feedUrl="http://example.com/feed",
        )

    @pytest.fixture
    def mock_fetch_genre(self, mocker, feed):
        return mocker.patch(
            "listenwave.podcasts.itunes.fetch_genre", return_value=[feed]
        )

    @pytest.fixture
    def mock_fetch_chart(self, mocker, feed):
        return mocker.patch(
            "listenwave.podcasts.itunes.fetch_chart", return_value=[feed]
        )

    @pytest.mark.django_db
    def test_fetch_chart(self, mock_fetch_chart, mock_fetch_genre):
        fetch_itunes_feeds.enqueue(
            country=self.country,
            itunes_genre_id=None,
        )
        mock_fetch_chart.assert_called()
        mock_fetch_genre.assert_not_called()

    @pytest.mark.django_db
    def test_fetch_genre(self, mock_fetch_chart, mock_fetch_genre):
        fetch_itunes_feeds.enqueue(
            country=self.country,
            itunes_genre_id=self.itunes_genre_id,
        )
        mock_fetch_chart.assert_not_called()
        mock_fetch_genre.assert_called()
