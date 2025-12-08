import pytest

from listenwave.feedparser.tasks import parse_feed
from listenwave.podcasts.models import Podcast


class TestParseFeed:
    @pytest.mark.django_db
    def test_ok(self, mocker, podcast) -> None:
        mock_parse = mocker.patch(
            "listenwave.feedparser.tasks.feed_parser.parse_feed",
            return_value=Podcast.ParserResult.SUCCESS,
        )

        parse_feed.enqueue(podcast_id=podcast.id)

        mock_parse.assert_called()
