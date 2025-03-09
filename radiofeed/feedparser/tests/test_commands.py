import pathlib

import pytest
from django.core.management import call_command

from radiofeed.feedparser.exceptions import DuplicateError
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestImportOpml:
    patched = "radiofeed.feedparser.opml_parser.parse_opml"

    @pytest.fixture
    def filename(self):
        return pathlib.Path(__file__).parent / "mocks" / "feeds.opml"

    @pytest.mark.django_db
    def test_command(self, mocker, filename):
        patched = mocker.patch(self.patched, return_value=iter(["https://example.com"]))
        call_command("import_opml", filename)
        assert Podcast.objects.count() == 1
        podcast = Podcast.objects.first()
        assert podcast is not None
        patched.assert_called()

    @pytest.mark.django_db
    def test_empty(self, mocker, filename):
        patched = mocker.patch(self.patched, return_value=iter([]))
        call_command("import_opml", filename)
        assert Podcast.objects.count() == 0
        patched.assert_called()


class TestExportFeeds:
    @pytest.mark.django_db
    def test_ok(self, podcast):
        call_command("export_opml", "-")

    @pytest.mark.django_db
    def test_promoted(self, podcast):
        call_command("export_opml", "-", promoted=True)


class TestParseFeeds:
    @pytest.fixture
    def mock_parse_ok(self, mocker):
        return mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
        )

    @pytest.fixture
    def mock_parse_fail(self, mocker):
        return mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
            side_effect=DuplicateError(),
        )

    @pytest.mark.django_db()(transaction=True)
    def test_ok(self, mock_parse_ok):
        PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parse_ok.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_not_scheduled(self, mock_parse_ok):
        PodcastFactory(active=False)
        call_command("parse_feeds")
        mock_parse_ok.assert_not_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_parser_error(self, mock_parse_fail):
        PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parse_fail.assert_called()
