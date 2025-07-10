import pytest
from django.core.cache import cache
from django.core.management import CommandError, call_command

from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestParseFeeds:
    _PARSE_FEED = "radiofeed.feedparser.management.commands.parse_feeds.parse_feed"

    @pytest.mark.django_db()(transaction=True)
    def test_ok(self, mocker):
        mock_parse = mocker.patch(
            self._PARSE_FEED,
            return_value=Podcast.ParserResult.SUCCESS,
        )
        PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parse.assert_called()

    @pytest.mark.django_db
    @pytest.mark.usefixtures("_locmem_cache")
    def test_locked(self, mocker):
        cache.set("parse-feeds-lock", value=True, timeout=60)
        mock_parse = mocker.patch(self._PARSE_FEED)
        PodcastFactory(pub_date=None)
        with pytest.raises(CommandError):
            call_command("parse_feeds")
        mock_parse.assert_not_called()

    @pytest.mark.django_db()(transaction=True)
    def test_not_scheduled(self, mocker):
        mock_parse = mocker.patch(self._PARSE_FEED)
        PodcastFactory(active=False)
        call_command("parse_feeds")
        mock_parse.assert_not_called()
