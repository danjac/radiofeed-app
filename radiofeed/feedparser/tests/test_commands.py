import json

import pytest
from django.core.management import call_command

from radiofeed.feedparser.exceptions import Duplicate
from radiofeed.podcasts.factories import create_podcast


class TestPodping:
    def _mock_stream(self, mocker, json_data, op_id="pp_podcast_update"):
        mocker.patch("beem.nodelist.NodeList.update_nodes")
        mocker.patch(
            "beem.nodelist.NodeList.get_hive_nodes",
            return_value=["https://api.hive.blog"],
        )
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
    def test_ok(self, mocker, podcast):
        self._mock_stream(mocker, {"urls": [podcast.rss]})
        call_command("podping")
        podcast.refresh_from_db()
        assert podcast.queued
        assert podcast.podping

    @pytest.mark.django_db
    def test_invalid_op_id(self, mocker, podcast):
        self._mock_stream(mocker, {"urls": [podcast.rss]}, "sm-incorrect")
        call_command("podping")
        podcast.refresh_from_db()
        assert not podcast.queued
        assert not podcast.podping

    @pytest.mark.django_db
    def test_single_url(self, mocker, podcast):
        self._mock_stream(mocker, {"url": podcast.rss})
        call_command("podping")
        podcast.refresh_from_db()
        assert podcast.queued
        assert podcast.podping

    @pytest.mark.django_db
    def test_no_matching_urls(self, mocker, podcast):
        self._mock_stream(mocker, {"urls": ["https//random/url.com"]})
        call_command("podping")
        podcast.refresh_from_db()
        assert not podcast.queued
        assert not podcast.podping


class TestParseFeeds:
    @pytest.fixture
    def mock_parse_ok(self, mocker):
        yield mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser.parse",
        )

    @pytest.fixture
    def mock_parse_fail(self, mocker):
        yield mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser.parse", side_effect=Duplicate()
        )

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
