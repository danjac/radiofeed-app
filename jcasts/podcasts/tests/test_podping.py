import json

from datetime import timedelta

import pytest

from jcasts.podcasts import podping


class TestRun:
    def test_single_url(self, mocker, podcast, mock_feed_queue):
        post = {
            "json": json.dumps(
                {
                    "url": podcast.rss,
                }
            )
        }

        mocker.patch("jcasts.podcasts.podping.get_stream", return_value=[post])

        for url in podping.run(timedelta(minutes=15)):
            assert url == podcast.rss

        assert podcast.id in mock_feed_queue.enqueued

    def test_multiple_urls(self, mocker, podcast, mock_feed_queue):
        post = {
            "json": json.dumps(
                {
                    "urls": [podcast.rss],
                }
            )
        }

        mocker.patch("jcasts.podcasts.podping.get_stream", return_value=[post])

        for url in podping.run(timedelta(minutes=15)):
            assert url == podcast.rss

        assert podcast.id in mock_feed_queue.enqueued


class TestGetStream:
    def test_ok(self, mocker, mock_get_estimated_block_num, mock_get_following):

        stream = [{"id": "podping", "required_posting_auths": ["test_acct"]}]

        mocker.patch(
            "jcasts.podcasts.podping.Blockchain.stream", return_value=iter(stream)
        )

        assert len(list(podping.get_stream(timedelta(minutes=15)))) == 1

    def test_id_mismatch(
        self, mocker, mock_get_estimated_block_num, mock_get_following
    ):

        stream = [{"id": "invalid", "required_posting_auths": ["test_acct"]}]

        mocker.patch(
            "jcasts.podcasts.podping.Blockchain.stream", return_value=iter(stream)
        )

        assert len(list(podping.get_stream(timedelta(minutes=15)))) == 0

    def test_invalid_acct(
        self, mocker, mock_get_estimated_block_num, mock_get_following
    ):

        stream = [{"id": "podping", "required_posting_auths": ["invalid"]}]

        mocker.patch(
            "jcasts.podcasts.podping.Blockchain.stream", return_value=iter(stream)
        )

        assert len(list(podping.get_stream(timedelta(minutes=15)))) == 0

    @pytest.fixture
    def mock_get_following(self, mocker):
        return mocker.patch(
            "jcasts.podcasts.podping.Account.get_following",
            return_value=["test_acct"],
        )

    @pytest.fixture
    def mock_get_estimated_block_num(sel, mocker):
        return mocker.patch(
            "jcasts.podcasts.podping.Blockchain.get_estimated_block_num",
            return_value=100,
        )
