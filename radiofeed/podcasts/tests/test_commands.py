from datetime import timedelta

import pytest

from django.core.management import call_command
from django.utils import timezone

from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.itunes import Feed
from radiofeed.podcasts.management.commands import feed_updater


class TestRecommender:
    def test_create_recommendations(self, mocker):
        patched = mocker.patch("radiofeed.podcasts.recommender.recommend")
        call_command("recommender")
        patched.assert_called()

    def test_send_recommendations(self, db, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.tasks.send_recommendations_email.map"
        )

        call_command("recommender", email=True)
        patched.assert_called()


class TestItunesCrawler:
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
        call_command("itunes_crawler")
        patched.assert_called()


class TestFeedUpdater:
    def test_command(self, db, mocker):

        patched = mocker.patch(
            "radiofeed.podcasts.tasks.feed_update.map",
        )

        call_command("feed_updater", limit=200)

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

        assert feed_updater.Command().get_scheduled_feeds().exists() == exists
