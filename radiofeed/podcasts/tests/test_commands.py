from datetime import timedelta

import httpx
import pytest
from django.core.management import call_command
from django.utils import timezone

from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import ItunesSearch
from radiofeed.podcasts.tests.factories import (
    ItunesSearchFactory,
    RecommendationFactory,
)


class TestClearItunesSearches:
    @pytest.mark.django_db()
    def test_delete_old_enough(self):
        ItunesSearchFactory(completed=timezone.now() - timedelta(hours=25))
        call_command("clear_itunes_searches")
        assert ItunesSearch.objects.exists() is False

    @pytest.mark.django_db()
    def test_delete_not_old_enough(self):
        ItunesSearchFactory(completed=timezone.now() - timedelta(hours=5))
        call_command("clear_itunes_searches")
        assert ItunesSearch.objects.exists() is True

    @pytest.mark.django_db()
    def test_delete_not_completed(self):
        ItunesSearchFactory(completed=None)
        call_command("clear_itunes_searches")
        assert ItunesSearch.objects.exists() is True


class TestParseItunes:
    @pytest.mark.django_db()
    def test_parse_ok(self, mocker):
        feeds = [itunes.Feed(title="test", rss="https://example.com")]
        mock_itunes_search = mocker.patch(
            "radiofeed.podcasts.itunes.search", return_value=feeds
        )

        ItunesSearchFactory()

        call_command("parse_itunes")

        mock_itunes_search.assert_called()

    @pytest.mark.django_db()
    def test_parse_error(self, mocker):
        mock_itunes_search = mocker.patch(
            "radiofeed.podcasts.itunes.search", side_effect=httpx.HTTPError("error")
        )

        ItunesSearchFactory()

        call_command("parse_itunes")

        mock_itunes_search.assert_called()

    @pytest.mark.django_db()
    def test_parse_already_completed(self, mocker):
        mock_itunes_search = mocker.patch("radiofeed.podcasts.itunes.search")

        ItunesSearchFactory(completed=timezone.now())

        call_command("parse_itunes")

        mock_itunes_search.assert_not_called()


class TestCreateRecommendations:
    @pytest.mark.django_db()
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
        call_command("send_recommendations_emails")
        patched.assert_called()
