import pytest

from radiofeed.feedparser.exceptions import DuplicateError
from radiofeed.feedparser.tasks import parse_feed, parse_feeds
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestParseFeeds:
    _PARSE_FEED = "radiofeed.feedparser.tasks.parse_feed.delay"

    @pytest.mark.django_db
    def test_ok(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED)
        PodcastFactory(pub_date=None)
        parse_feeds()
        mock_parse.assert_called()

    @pytest.mark.django_db
    def test_not_scheduled(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED)
        PodcastFactory(active=False)
        parse_feeds()
        mock_parse.assert_not_called()


class TestParseFeed:
    _PARSE_FEED = "radiofeed.feedparser.feed_parser.parse_feed"

    @pytest.mark.django_db
    def test_feed_parser_ok(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED)
        podcast = PodcastFactory(pub_date=None)
        parse_feed(podcast.pk)
        mock_parse.assert_called()

    @pytest.mark.django_db
    def test_feed_parser_error(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED, side_effect=DuplicateError())
        podcast = PodcastFactory(pub_date=None)
        parse_feed(podcast.pk)
        mock_parse.assert_called()
