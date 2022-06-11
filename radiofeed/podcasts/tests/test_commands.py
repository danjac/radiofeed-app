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
    def test_create_recommendations(self, mocker):
        patched = mocker.patch("radiofeed.podcasts.recommender.recommend")
        call_command("create_recommendations")
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
            "radiofeed.podcasts.emails.send_recommendations_email.delay"
        )

        call_command("send_recommendation_emails")
        patched.assert_called_with(user.id)

    @pytest.mark.parametrize(
        "active,queued,pub_date,parsed,called",
        [
            (
                True,
                False,
                None,
                None,
                True,
            ),
            (
                False,
                False,
                None,
                None,
                False,
            ),
            (
                True,
                False,
                timedelta(hours=3),
                timedelta(hours=1),
                True,
            ),
            (
                True,
                True,
                timedelta(hours=3),
                timedelta(hours=1),
                False,
            ),
            (
                True,
                False,
                timedelta(hours=3),
                timedelta(minutes=30),
                False,
            ),
            (
                True,
                False,
                timedelta(days=3),
                timedelta(hours=3),
                True,
            ),
            (
                True,
                False,
                timedelta(days=3),
                timedelta(hours=1),
                False,
            ),
            (
                True,
                False,
                timedelta(days=8),
                timedelta(hours=8),
                True,
            ),
            (
                True,
                False,
                timedelta(days=8),
                timedelta(hours=9),
                True,
            ),
            (
                True,
                False,
                timedelta(days=14),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                False,
                timedelta(days=15),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                False,
                timedelta(days=15),
                timedelta(hours=24),
                True,
            ),
        ],
    )
    def test_parse_podcast_feeds(
        self, db, mocker, active, queued, pub_date, parsed, called
    ):
        now = timezone.now()

        podcast = PodcastFactory(
            active=active,
            queued=now if queued else None,
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
        )

        patched = mocker.patch(
            "radiofeed.podcasts.parsers.feed_parser.parse_podcast_feed.delay"
        )

        call_command("parse_podcast_feeds")
        if called:
            patched.assert_called_with(podcast.id)
        else:
            patched.assert_not_called()

        assert Podcast.objects.filter(queued__isnull=False).exists() == called or queued
