import pathlib

from datetime import timedelta

import pytest

from django.core.management import call_command
from django.utils import timezone

from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.itunes import Feed
from radiofeed.podcasts.models import Podcast
from radiofeed.users.factories import UserFactory


class TestCreateRecommendations:
    def test_command(self, mocker):
        patched = mocker.patch("radiofeed.podcasts.recommender.recommend")
        call_command("create_recommendations")
        patched.assert_called()


class TestCrawlItunes:
    def test_command(self, mocker, podcast):
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


class TestImportPodcasts:
    def test_command(self, db):
        call_command(
            "import_podcasts",
            pathlib.Path(__file__).parent / "mocks" / "feeds.txt",
        )

        assert Podcast.objects.count() == 18


class TestExportPodcasts:
    def test_command(self, mocker, podcast):
        mocker.patch("builtins.open")
        mock_writer = mocker.Mock()
        mocker.patch("csv.writer", return_value=mock_writer)
        call_command("export_podcasts", "filename.txt")
        mock_writer.writerow.assert_called_with([podcast.rss])


class TestSendRecommendationsEmails:
    def test_command(self, db, mocker):
        user = UserFactory(send_email_notifications=True)
        UserFactory(send_email_notifications=False)

        patched = mocker.patch(
            "radiofeed.podcasts.emails.send_recommendations_email.delay"
        )

        call_command("send_recommendation_emails")
        patched.assert_called_with(user.id)


class TestParsePodcastFeeds:
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
    def test_command(self, db, mocker, active, queued, pub_date, parsed, called):
        now = timezone.now()

        podcast = PodcastFactory(
            active=active,
            queued=now if queued else None,
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
        )

        patched = mocker.patch(
            "radiofeed.podcasts.management.commands.parse_podcast_feeds.feed_parser.enqueue",
        )

        call_command("parse_podcast_feeds")

        if called:
            patched.assert_called_with(podcast.id, job_timeout=300)
        else:
            patched.assert_called_with(job_timeout=300)
