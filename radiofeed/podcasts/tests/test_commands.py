import pathlib

from datetime import timedelta

import pytest

from django.core.management import call_command
from django.utils import timezone

from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.itunes import Feed
from radiofeed.podcasts.models import Podcast
from radiofeed.users.factories import UserFactory


class TestCommands:
    def test_recommend(self, mocker):
        patched = mocker.patch("radiofeed.podcasts.recommender.recommend")
        call_command("recommend")
        patched.assert_called()

    def test_crawl_itunes(self, mocker, podcast):
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.crawl",
            return_value=[
                Feed(
                    title="test 1",
                    url="https://example1.com",
                    rss="https://example1.com/test.xml",
                ),
                Feed(
                    title="test 2",
                    url="https://example2.com",
                    rss=podcast.rss,
                    podcast=podcast,
                ),
            ],
        )
        call_command("crawl_itunes")
        patched.assert_called()

    def test_import_podcasts(self, db):
        call_command(
            "import_podcasts",
            pathlib.Path(__file__).parent / "mocks" / "feeds.txt",
        )

        assert Podcast.objects.count() == 18

    def test_export_podcasts(self, mocker, podcast):
        mocker.patch("builtins.open")
        mock_writer = mocker.Mock()
        mocker.patch("csv.writer", return_value=mock_writer)
        call_command("export_podcasts", "filename.txt")
        mock_writer.writerow.assert_called_with([podcast.rss])

    def test_send_recommendations_emails(self, db, mocker):
        user = UserFactory(send_email_notifications=True)
        UserFactory(send_email_notifications=False)

        patched = mocker.patch(
            "radiofeed.podcasts.tasks.send_recommendations_email.map"
        )

        call_command("send_recommendation_emails")
        assert list(patched.mock_calls[0][1][0]) == [(user.id,)]

    @pytest.mark.parametrize(
        "active,pub_date,parsed,called",
        [
            (
                True,
                None,
                None,
                True,
            ),
            (
                False,
                None,
                None,
                False,
            ),
            (
                True,
                timedelta(hours=3),
                timedelta(hours=1),
                True,
            ),
            (
                True,
                timedelta(hours=3),
                timedelta(minutes=30),
                False,
            ),
            (
                True,
                timedelta(days=3),
                timedelta(hours=3),
                True,
            ),
            (
                True,
                timedelta(days=3),
                timedelta(hours=1),
                False,
            ),
            (
                True,
                timedelta(days=8),
                timedelta(hours=8),
                True,
            ),
            (
                True,
                timedelta(days=14),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                timedelta(days=14),
                timedelta(hours=24),
                True,
            ),
        ],
    )
    def test_parse_podcast_feeds(self, db, mocker, active, pub_date, parsed, called):
        now = timezone.now()

        podcast = PodcastFactory(
            active=active,
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
        )

        patched = mocker.patch("radiofeed.podcasts.tasks.parse_podcast_feed.map")

        call_command("parse_podcast_feeds")

        calls = list(patched.mock_calls[0][1][0])
        if called:
            assert calls == [(podcast.id,)]
        else:
            assert calls == []
