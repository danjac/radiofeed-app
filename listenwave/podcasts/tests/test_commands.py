import pytest
from django.core.management import call_command

from listenwave.podcasts.tests.factories import CategoryFactory, RecommendationFactory
from listenwave.users.tests.factories import EmailAddressFactory


class TestFetchTopItunes:
    @pytest.fixture
    def category(self):
        return CategoryFactory(itunes_genre_id=1301)

    @pytest.fixture
    def mock_fetch_itunes_feeds(self, mocker):
        return mocker.patch(
            "listenwave.podcasts.tasks.fetch_itunes_feeds",
            return_value=mocker.MagicMock,
        )

    @pytest.mark.django_db
    def test_ok(self, category, mock_fetch_itunes_feeds):
        call_command("fetch_top_itunes")
        mock_fetch_itunes_feeds.enqueue.assert_called()


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
        return EmailAddressFactory(verified=True, primary=True)

    @pytest.fixture
    def mock_send_recommendations(self, mocker):
        return mocker.patch(
            "listenwave.podcasts.tasks.send_recommendations",
            return_value=mocker.MagicMock,
        )

    @pytest.mark.django_db(transaction=True)
    def test_ok(self, recipient, mock_send_recommendations):
        call_command("send_recommendations")
        mock_send_recommendations.enqueue.assert_called()
