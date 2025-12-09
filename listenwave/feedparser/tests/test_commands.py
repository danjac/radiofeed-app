import pytest
from django.core.management import call_command

from listenwave.podcasts.tests.factories import PodcastFactory


class TestParseFeeds:
    @pytest.fixture
    def mock_parse(self, mocker):
        return mocker.patch(
            "listenwave.feedparser.management.commands.parse_feeds.parse_feed"
        )

    @pytest.mark.django_db
    def test_ok(self, mock_parse):
        PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parse.assert_called()

    @pytest.mark.django_db
    def test_not_scheduled(self, mock_parse):
        PodcastFactory(active=False)
        call_command("parse_feeds")
        mock_parse.assert_not_called()
