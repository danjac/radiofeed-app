from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.tasks import (
    parse_podcast_feed,
    recommend,
    schedule_podcast_feeds,
    send_recommendations_email,
    send_recommendations_emails,
)
from radiofeed.users.factories import UserFactory


class TestTasks:
    @pytest.fixture
    def mock_parse_podcast_feed(self, mocker):
        return mocker.patch("radiofeed.podcasts.tasks.parse_podcast_feed")

    def test_schedule_podcast_feeds_not_parsed(self, db, mock_parse_podcast_feed):
        podcast = PodcastFactory(parsed=None)
        schedule_podcast_feeds()
        mock_parse_podcast_feed.assert_called_with(podcast.id)

    def test_schedule_podcast_feeds_recently_parsed(self, db, mock_parse_podcast_feed):
        PodcastFactory(parsed=timezone.now() - timedelta(minutes=12))
        schedule_podcast_feeds()
        mock_parse_podcast_feed.assert_not_called()

    def test_schedule_podcast_feeds_is_scheduled(self, db, mock_parse_podcast_feed):
        podcast = PodcastFactory(parsed=timezone.now() - timedelta(hours=12))
        schedule_podcast_feeds()
        mock_parse_podcast_feed.assert_called_with(podcast.id)

    def test_schedule_podcast_feeds_inactive(self, db, mock_parse_podcast_feed):
        PodcastFactory(parsed=timezone.now() - timedelta(hours=12), active=False)
        schedule_podcast_feeds()
        mock_parse_podcast_feed.assert_not_called()

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
