import pytest

from radiofeed.feedparser.exceptions import DuplicateError
from radiofeed.feedparser.management.commands.feedparser import parse_feeds
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestParseFeeds:
    _PARSE_FEED = "radiofeed.feedparser.management.commands.feedparser.parse_feed"

    @pytest.mark.django_db()(transaction=True)
    def test_ok(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED)
        PodcastFactory(pub_date=None)
        parse_feeds()
        mock_parse.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_not_scheduled(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED)
        PodcastFactory(active=False)
        parse_feeds()
        mock_parse.assert_not_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_parser_error(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED, side_effect=DuplicateError())
        PodcastFactory(pub_date=None)
        parse_feeds()
        mock_parse.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_other_exception(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED, side_effect=RuntimeError())
        PodcastFactory(pub_date=None)
        parse_feeds()
        mock_parse.assert_called()
