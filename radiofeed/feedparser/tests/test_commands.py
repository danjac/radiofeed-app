import pytest
from django.core.management import call_command

from radiofeed.podcasts.factories import create_podcast


class TestParseFeeds:
    @pytest.fixture
    def mock_enqueue(self, mocker):
        def _mock_enqueue(fn, *args, **kwargs):
            fn(*args, **kwargs)

        mocker.patch("django_rq.enqueue", _mock_enqueue)

    @pytest.fixture
    def mock_parse(self, mocker):
        yield mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
        )

    @pytest.mark.django_db
    def test_ok(self, mock_enqueue, mock_parse):
        create_podcast(pub_date=None)
        call_command("parse_feeds", limit=200)
        mock_parse.assert_called()
