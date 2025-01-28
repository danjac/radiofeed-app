import pytest

from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.podcasts.templatetags.podcasts import get_podcast_seasons


class TestGetPodcastSeasons:
    @pytest.mark.django_db
    def test_seasons_none(self, podcast):
        assert get_podcast_seasons(podcast, 1) == {"current": None, "items": []}

    @pytest.mark.django_db
    def test_seasons(self, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast, season=1)
        EpisodeFactory.create_batch(2, podcast=podcast, season=2)
        seasons = get_podcast_seasons(podcast, 1)
        assert seasons["current"]["label"] == "Season 1"
        assert len(seasons["items"]) == 2
        assert seasons["items"][0]["label"] == "All Seasons"
        assert seasons["items"][1]["label"] == "Season 2"
