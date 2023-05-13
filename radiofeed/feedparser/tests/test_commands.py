import json
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from radiofeed.feedparser.exceptions import Duplicate
from radiofeed.podcasts.factories import create_podcast


@pytest.fixture
def mock_parse_ok(mocker):
    yield mocker.patch(
        "radiofeed.feedparser.feed_parser.FeedParser.parse",
    )


@pytest.fixture
def mock_parse_fail(mocker):
    yield mocker.patch(
        "radiofeed.feedparser.feed_parser.FeedParser.parse", side_effect=Duplicate()
    )


class TestPodping:
    def _mock_stream(self, mocker, json_data, op_id="pp_podcast_update"):
        return mocker.patch(
            "beem.blockchain.Blockchain.stream",
            return_value=[
                {
                    "id": op_id,
                    "json": json.dumps(json_data),
                }
            ],
        )

    @pytest.mark.django_db
    def test_ok(self, mocker, podcast, mock_parse_ok):
        self._mock_stream(mocker, {"urls": [podcast.rss]})
        call_command("podping")
        mock_parse_ok.assert_called()

    @pytest.mark.django_db
    def test_invalid_op_id(self, mocker, podcast, mock_parse_ok):
        self._mock_stream(mocker, {"urls": [podcast.rss]}, "sm-incorrect")
        call_command("podping")
        mock_parse_ok.assert_not_called()

    @pytest.mark.django_db
    def test_parsed_more_than_15_min_ago(self, mocker, mock_parse_ok):
        podcast = create_podcast(parsed=timezone.now() - timedelta(minutes=30))
        self._mock_stream(mocker, {"urls": [podcast.rss]})
        call_command("podping")
        mock_parse_ok.assert_called()

    @pytest.mark.django_db
    def test_parsed_less_than_15_min_ago(self, mocker, mock_parse_ok):
        podcast = create_podcast(parsed=timezone.now() - timedelta(minutes=12))
        self._mock_stream(mocker, {"urls": [podcast.rss]})
        call_command("podping")
        mock_parse_ok.assert_not_called()

    @pytest.mark.django_db
    def test_single_url(self, mocker, podcast, mock_parse_ok):
        self._mock_stream(mocker, {"url": podcast.rss})
        call_command("podping")
        mock_parse_ok.assert_called()

    @pytest.mark.django_db
    def test_fail(self, mocker, podcast, mock_parse_fail):
        self._mock_stream(mocker, {"urls": [podcast.rss]})
        call_command("podping")
        mock_parse_fail.assert_called()


class TestParseFeeds:
    @pytest.mark.django_db
    def test_ok(self, mock_parse_ok):
        create_podcast(pub_date=None)
        call_command("parse_feeds", limit=200)
        mock_parse_ok.assert_called()

    @pytest.mark.django_db
    def test_feed_parser_error(self, mock_parse_fail):
        create_podcast(pub_date=None)
        call_command("parse_feeds", limit=200)
        mock_parse_fail.assert_called()
