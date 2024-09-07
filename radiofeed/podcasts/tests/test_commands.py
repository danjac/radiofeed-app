import pytest

from radiofeed.podcasts.management.commands.podcasts import cli
from radiofeed.podcasts.tests.factories import RecommendationFactory


class TestCreateRecommendations:
    @pytest.mark.django_db
    def test_create_recommendations(self, mocker, cli_runner):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=[
                ("en", RecommendationFactory.create_batch(3)),
            ],
        )
        result = cli_runner.invoke(cli, ["create_recommendations"])
        assert result.exit_code == 0
        patched.assert_called()

    @pytest.mark.django_db
    def test_verbose(self, mocker, cli_runner):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=[
                ("en", RecommendationFactory.create_batch(3)),
            ],
        )

        result = cli_runner.invoke(cli, ["create_recommendations"])
        assert result.exit_code == 0
        patched.assert_called()


class TestSendRecommendationsEmails:
    @pytest.mark.django_db()(transaction=True)
    def test_send_emails(self, mocker, cli_runner, user):
        patched = mocker.patch("radiofeed.podcasts.emails.send_recommendations_email")
        result = cli_runner.invoke(cli, ["send_recommendations_emails"])
        assert result.exit_code == 0
        patched.assert_called()
