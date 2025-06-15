import pytest

from radiofeed.feedparser.exceptions import DuplicateError
from radiofeed.feedparser.tasks import parse_feed, parse_feeds
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestParseFeeds:
    _ASYNC_TASK = "radiofeed.feedparser.tasks.async_task"

    @pytest.mark.django_db
    def test_ok(self, mocker):
        mock_task = mocker.patch(self._ASYNC_TASK)
        PodcastFactory(pub_date=None)
        parse_feeds()
        mock_task.assert_called()

    @pytest.mark.django_db
    def test_not_scheduled(self, mocker):
        mock_task = mocker.patch(self._ASYNC_TASK)
        PodcastFactory(active=False)
        parse_feeds()
        mock_task.assert_not_called()


class TestParseFeed:
    _PARSE_FEED = "radiofeed.feedparser.feed_parser.parse_feed"

    @pytest.mark.django_db
    def test_ok(self, mocker, podcast):
        mock_parse = mocker.patch(self._PARSE_FEED)
        parse_feed(podcast.id)
        mock_parse.assert_called()

    @pytest.mark.django_db
    def test_parser_error(self, mocker, podcast):
        mock_parse = mocker.patch(self._PARSE_FEED, side_effect=DuplicateError())
        parse_feed(podcast.id)
        mock_parse.assert_called()
