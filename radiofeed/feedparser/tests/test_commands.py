import pathlib

import pytest
from django.core.management import call_command

from radiofeed.feedparser.exceptions import DuplicateError
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestImportOpml:
    @pytest.mark.django_db
    def test_import_opml(self):
        path = pathlib.Path(__file__).parent / "mocks" / "feeds.opml"
        call_command("import_opml", path)
        assert Podcast.objects.count() == 11


class TestParseFeeds:
    _PARSE_FEED = "radiofeed.feedparser.management.commands.parse_feeds.parse_feed"

    @pytest.mark.django_db()(transaction=True)
    def test_ok(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED)
        PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parse.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_not_scheduled(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED)
        PodcastFactory(active=False)
        call_command("parse_feeds")
        mock_parse.assert_not_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_parser_result(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED, side_effect=DuplicateError())
        PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parse.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_other_exception(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED, side_effect=RuntimeError())
        PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parse.assert_called()
