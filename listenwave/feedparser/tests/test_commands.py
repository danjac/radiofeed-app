from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from listenwave.podcasts.tests.factories import PodcastFactory


class TestParseFeeds:
    @pytest.fixture
    def mock_parse(self, mocker):
        return mocker.patch(
            "listenwave.feedparser.management.commands.parse_feeds.parse_feed",
            mocker.MagicMock(),
        )

    @pytest.mark.django_db
    def test_ok(self, mock_parse):
        podcast = PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parse.enqueue.assert_called_with(podcast_id=podcast.id, queued=None)
        podcast.refresh_from_db()
        assert podcast.queued is not None

    @pytest.mark.django_db
    def test_queued(self, mock_parse):
        PodcastFactory(pub_date=None, queued=timezone.now())
        call_command("parse_feeds")
        mock_parse.enqueue.assert_not_called()

    @pytest.mark.django_db
    def test_queued_more_than_3_hours(self, mock_parse):
        PodcastFactory(pub_date=None, queued=timezone.now() - timedelta(hours=6))
        call_command("parse_feeds")
        mock_parse.enqueue.assert_called()

    @pytest.mark.django_db
    def test_not_scheduled(self, mock_parse):
        PodcastFactory(active=False)
        call_command("parse_feeds")
        mock_parse.enqueue.assert_not_called()
