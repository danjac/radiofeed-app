import pathlib

import pytest

from radiofeed.feedparser.exceptions import DuplicateError
from radiofeed.feedparser.management.commands.feedparser import cli
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestParseOpml:
    patched = "radiofeed.feedparser.opml_parser.parse_opml"

    @pytest.fixture
    def filename(self):
        return pathlib.Path(__file__).parent / "mocks" / "feeds.opml"

    @pytest.mark.django_db
    def test_command(self, mocker, cli_runner, filename):
        patched = mocker.patch(self.patched, return_value=iter(["https://example.com"]))
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(cli, ["parse_opml", "--", filename])
            assert result.exit_code == 0
        assert Podcast.objects.count() == 1
        assert not Podcast.objects.first().promoted
        patched.assert_called()

    @pytest.mark.django_db
    def test_promote(self, mocker, cli_runner, filename):
        patched = mocker.patch(self.patched, return_value=iter(["https://example.com"]))
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(cli, ["parse_opml", "--promote", "--", filename])
            assert result.exit_code == 0
        assert Podcast.objects.count() == 1
        assert Podcast.objects.first().promoted
        patched.assert_called()

    @pytest.mark.django_db
    def test_empty(self, mocker, cli_runner, filename):
        patched = mocker.patch(self.patched, return_value=iter([]))
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(cli, ["parse_opml", "--", filename])
            assert result.exit_code == 0
        assert Podcast.objects.count() == 0
        patched.assert_called()


class TestExportFeeds:
    @pytest.mark.django_db
    def test_ok(self, cli_runner, podcast):
        with cli_runner.isolated_filesystem():
            cli_runner.invoke(cli, ["export_opml", "-"])

    @pytest.mark.django_db
    def test_promoted(self, cli_runner, podcast):
        with cli_runner.isolated_filesystem():
            cli_runner.invoke(cli, ["export_opml", "-", "--promoted"])


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
    def test_ok(self, cli_runner, mock_parse_ok):
        PodcastFactory(pub_date=None)
        result = cli_runner.invoke(cli, "parse_feeds")
        assert result.exit_code == 0
        mock_parse_ok.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_not_scheduled(self, cli_runner, mock_parse_ok):
        PodcastFactory(active=False)
        result = cli_runner.invoke(cli, "parse_feeds")
        assert result.exit_code == 0
        mock_parse_ok.assert_not_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_parser_error(self, cli_runner, mock_parse_fail):
        PodcastFactory(pub_date=None)
        result = cli_runner.invoke(cli, "parse_feeds")
        assert result.exit_code == 0
        mock_parse_fail.assert_called()
