import pytest
from django.core.management import call_command

from radiofeed.podcasts.tests.factories import RecommendationFactory


class TestCreateRecommendations:
    @pytest.mark.django_db
    def test_create_recommendations(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=[
                ("en", RecommendationFactory.create_batch(3)),
            ],
        )
        call_command("create_recommendations")
        patched.assert_called()


class TestSendRecommendationsEmails:
    @pytest.mark.django_db()(transaction=True)
    def test_send_emails(self, mocker, user):
        patched = mocker.patch("radiofeed.podcasts.emails.send_recommendations_email")
        call_command("send_recommendations")
        patched.assert_called()
