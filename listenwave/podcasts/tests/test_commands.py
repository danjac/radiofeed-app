import pytest
from django.core.management import call_command

from listenwave.podcasts.itunes import Feed, ItunesError
from listenwave.podcasts.models import Podcast
from listenwave.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from listenwave.users.tests.factories import EmailAddressFactory


class TestFetchTopItunes:
    @pytest.fixture
    def feed(self):
        return Feed(
            artworkUrl100="http://example.com/artwork.jpg",
            collectionName="Example Podcast",
            collectionViewUrl="http://example.com/podcast",
            feedUrl="http://example.com/feed",
        )

    @pytest.fixture
    def category(self):
        return CategoryFactory(itunes_genre_id=1301)

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
    def test_ok(
        self,
        category,
        mock_fetch_chart,
        mock_fetch_genre,
    ):
        call_command("fetch_top_itunes", jitter_min=0, jitter_max=0)
        mock_fetch_chart.assert_called()
        mock_fetch_genre.assert_called()

    @pytest.mark.django_db
    def test_fetch_top_feeds(
        self,
        category,
        mock_fetch_chart,
        mock_fetch_genre,
    ):
        promoted = PodcastFactory(promoted=True)
        call_command("fetch_top_itunes", jitter_min=0, jitter_max=0)

        mock_fetch_chart.assert_called()
        mock_fetch_genre.assert_called()

        # promoted podcast should be demoted
        promoted.refresh_from_db()
        assert promoted.promoted is False

        # only one podcast should be promoted, from new feed
        assert Podcast.objects.filter(promoted=True).count() == 1

    @pytest.mark.django_db
    def fetch_top_feeds_none_found(
        self,
        mocker,
        category,
        mock_fetch_genre,
    ):
        patched = mocker.patch(
            "listenwave.podcasts.itunes.fetch_chart",
            return_value=[],
        )
        promoted = PodcastFactory(promoted=True)
        call_command("fetch_top_itunes", jitter_min=0, jitter_max=0)
        patched.assert_called()

        # no promoted feeds found, so existing promoted podcast remains

        promoted.refresh_from_db()
        assert promoted.promoted is False

    @pytest.mark.django_db
    def test_chart_error(self, mocker, category, mock_fetch_genre):
        mock_fetch_chart = mocker.patch(
            "listenwave.podcasts.itunes.fetch_chart",
            side_effect=ItunesError("API error"),
        )
        call_command("fetch_top_itunes", jitter_min=0, jitter_max=0)
        mock_fetch_chart.assert_called()
        mock_fetch_chart.assert_called()

    @pytest.mark.django_db
    def test_genre_error(self, mocker, category, mock_fetch_chart):
        mock_fetch_genre = mocker.patch(
            "listenwave.podcasts.itunes.fetch_genre",
            side_effect=ItunesError("API error"),
        )
        call_command("fetch_top_itunes", jitter_min=0, jitter_max=0)
        mock_fetch_chart.assert_called()
        mock_fetch_genre.assert_called()


class TestCreateRecommendations:
    @pytest.mark.django_db
    def test_create_recommendations(self, mocker):
        patched = mocker.patch(
            "listenwave.podcasts.recommender.recommend",
            return_value=RecommendationFactory.create_batch(3),
        )
        call_command("create_recommendations")
        patched.assert_called()


class TestSendRecommendations:
    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(
            verified=True,
            primary=True,
        )

    @pytest.mark.django_db(transaction=True)
    def test_has_recommendations(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(subscriber=recipient.user)
        RecommendationFactory.create_batch(3, podcast=subscription.podcast)
        call_command("send_recommendations")
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [recipient.email]
        assert recipient.user.recommended_podcasts.count() == 3

    @pytest.mark.django_db(transaction=True)
    def test_has_no_recommendations(self, mailoutbox, recipient):
        call_command("send_recommendations")
        assert len(mailoutbox) == 0
        assert recipient.user.recommended_podcasts.count() == 0
