import pathlib

from datetime import timedelta

import pytest

from django.core.management import call_command
from django.utils import timezone

from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.itunes import Feed
from radiofeed.podcasts.management.commands import schedule_feed_updates
from radiofeed.podcasts.models import Podcast


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
        call_command("export_podcasts", output="filename.txt")
        mock_writer.writerow.assert_called_with([podcast.rss])


class TestSendRecommendationsEmails:
    def test_command(self, db, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.tasks.send_recommendations_email.map"
        )

        call_command("send_recommendation_emails")
        patched.assert_called()


class TestScheduleFeedUpdates:
    def test_command(self, db, mocker):

        patched = mocker.patch(
            "radiofeed.podcasts.tasks.feed_update.map",
        )
        mocker.patch("multiprocessing.cpu_count", return_value=4)

        call_command("schedule_feed_updates")

        patched.assert_called()

    @pytest.mark.parametrize(
        "active,pub_date,parsed,exists",
        [
            (
                True,
                None,
                None,
                True,
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
                timedelta(days=8),
                timedelta(hours=9),
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
                timedelta(days=15),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                timedelta(days=15),
                timedelta(hours=24),
                True,
            ),
        ],
    )
    def test_get_scheduled_feeds(self, db, mocker, active, pub_date, parsed, exists):
        now = timezone.now()

        PodcastFactory(
            active=active,
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
        )

        assert schedule_feed_updates.Command().get_scheduled_feeds().exists() == exists
