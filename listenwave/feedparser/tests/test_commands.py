import pytest
from django.core.management import call_command

from listenwave.podcasts.models import Podcast
from listenwave.podcasts.tests.factories import PodcastFactory


class TestParseFeeds:
    _PARSE_FEED = "listenwave.feedparser.management.commands.parse_feeds.parse_feed"

    @pytest.mark.django_db
    def test_ok(self, mocker):
        mock_parse = mocker.patch(
            self._PARSE_FEED,
            return_value=Podcast.ParserResult.SUCCESS,
        )
        PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parse.assert_called()

    @pytest.mark.django_db
    def test_not_scheduled(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED)
        PodcastFactory(active=False)
        call_command("parse_feeds")
        mock_parse.assert_not_called()
