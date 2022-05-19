import pytest

from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tasks import (
    parse_podcast_feed,
    recommend,
    schedule_frequent_feeds,
    schedule_primary_feeds,
    schedule_sporadic_feeds,
    send_recommendations_email,
    send_recommendations_emails,
)
from radiofeed.users.factories import UserFactory


class TestTasks:
    @pytest.fixture
    def mock_parse_podcast_feed(self, mocker):
        return mocker.patch("radiofeed.podcasts.tasks.parse_podcast_feed")

    def test_schedule_primary_feeds(self, db, mocker, mock_parse_podcast_feed):
        podcast = PodcastFactory(parsed=None)
        mocker.patch(
            "radiofeed.podcasts.tasks.scheduler.get_primary_podcasts",
            return_value=Podcast.objects.all(),
        )
        schedule_primary_feeds()
        mock_parse_podcast_feed.assert_called_with(podcast.id)

    def test_schedule_frequent_feeds(self, db, mocker, mock_parse_podcast_feed):
        podcast = PodcastFactory(parsed=None)
        mocker.patch(
            "radiofeed.podcasts.tasks.scheduler.get_frequent_podcasts",
            return_value=Podcast.objects.all(),
        )
        schedule_frequent_feeds()
        mock_parse_podcast_feed.assert_called_with(podcast.id)

    def test_schedule_sporadic_feeds(self, db, mocker, mock_parse_podcast_feed):
        podcast = PodcastFactory(parsed=None)
        mocker.patch(
            "radiofeed.podcasts.tasks.scheduler.get_sporadic_podcasts",
            return_value=Podcast.objects.all(),
        )
        schedule_sporadic_feeds()
        mock_parse_podcast_feed.assert_called_with(podcast.id)

    def test_parse_podcast_feed(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.tasks.feed_parser.parse_podcast_feed"
        )
        parse_podcast_feed(1)
        patched.assert_called_with(1)

    def test_send_recommendations_email(self, mocker, user):
        patched = mocker.patch(
            "radiofeed.podcasts.tasks.emails.send_recommendations_email"
        )
        send_recommendations_email(user.id)
        patched.assert_called_with(user)

    def test_send_recommendations_email_no_user(self, db, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.tasks.emails.send_recommendations_email"
        )
        send_recommendations_email(1234)
        patched.assert_not_called()

    def test_recommend(self, mocker):
        patched = mocker.patch("radiofeed.podcasts.tasks.recommender.recommend")
        recommend()
        patched.assert_called()

    def test_send_recommendations_emails(self, db, mocker):
        sent = []

        class MockSend:
            def __init__(self, user_id):
                self.user_id = user_id

            def __call__(self):
                sent.append(self.user_id)

        send = UserFactory(send_email_notifications=True)
        not_send = UserFactory(send_email_notifications=False)

        mocker.patch("radiofeed.podcasts.tasks.send_recommendations_email", MockSend)

        send_recommendations_emails()

        assert send.id in sent
        assert not_send.id not in sent
