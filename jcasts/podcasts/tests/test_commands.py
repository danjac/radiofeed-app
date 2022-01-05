import pytest
import requests

from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from jcasts.podcasts.factories import CategoryFactory, PodcastFactory
from jcasts.podcasts.itunes import Feed
from jcasts.podcasts.models import Category, Podcast, Recommendation
from jcasts.users.factories import UserFactory


class TestFetchTopRated:
    def test_command(self, mocker):
        mock_top_rated = mocker.patch(
            "jcasts.podcasts.itunes.top_rated",
            return_value=[
                Feed(
                    rss="https://example.com/test.xml",
                    url="https://example.com/id2345",
                )
            ],
        )
        call_command("fetch_top_rated")
        mock_top_rated.assert_called()

    def test_exception(self, mocker):
        mocker.patch("jcasts.podcasts.itunes.top_rated", side_effect=requests.HTTPError)
        with pytest.raises(CommandError):
            call_command("fetch_top_rated")


class TestCrawlItunes:
    def test_command(self, mocker):
        mock_top_rated = mocker.patch(
            "jcasts.podcasts.itunes.crawl",
            return_value=[
                Feed(
                    rss="https://example.com",
                    url="https://example.com/id2345",
                )
            ],
        )
        call_command("crawl_itunes")
        mock_top_rated.assert_called()

    def test_exception(self, mocker):
        mocker.patch("jcasts.podcasts.itunes.crawl", side_effect=requests.HTTPError)
        with pytest.raises(CommandError):
            call_command("crawl_itunes")


class TestClearFeedQueue:
    def test_queue(self, db, mock_feed_queue):
        now = timezone.now()

        podcast = PodcastFactory(queued=now, feed_queue="feeds")

        call_command("clear_feed_queue", ["feeds"])

        podcast.refresh_from_db()
        assert not podcast.queued

    def test_all(self, db, mock_feed_queue):
        now = timezone.now()

        podcast = PodcastFactory(queued=now, feed_queue="feeds")

        call_command("clear_feed_queue", all=True)

        podcast.refresh_from_db()
        assert not podcast.queued


class TestSeedPodcastData:
    def test_command(self, db):

        call_command("seed_podcast_data")

        assert Category.objects.count() == 110
        assert Podcast.objects.count() == 294


class TestSendRecommendationEmails:
    def test_command(self, db, mocker):

        yes = UserFactory(send_email_notifications=True)
        UserFactory(send_email_notifications=False)
        UserFactory(send_email_notifications=True, is_active=False)

        mock_send = mocker.patch(
            "jcasts.podcasts.emails.send_recommendations_email.delay"
        )

        call_command("send_recommendation_emails")

        assert len(mock_send.mock_calls) == 1
        assert mock_send.call_args == ((yes,),)


class TestMakeRecommendations:
    def test_command(self, db):
        category = CategoryFactory(name="Science")

        PodcastFactory(
            extracted_text="Cool science podcast science physics astronomy",
            categories=[category],
        )
        PodcastFactory(
            extracted_text="Another cool science podcast science physics astronomy",
            categories=[category],
        )

        call_command("make_recommendations")

        assert Recommendation.objects.count() == 2


class TestSchedulePodcastFeeds:
    def test_primary(self, db, mock_feed_queue):
        podcast = PodcastFactory(promoted=True)
        call_command("schedule_podcast_feeds", primary=True)
        assert podcast.id in mock_feed_queue.enqueued

    def test_secondary(self, db, mock_feed_queue):
        podcast = PodcastFactory(pub_date=None)
        call_command("schedule_podcast_feeds", after=24)
        assert podcast.id in mock_feed_queue.enqueued
