import pytest

from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.podcasts.templatetags.podcasts import get_podcast_seasons


class TestGetPodcastSeasons:
    @pytest.mark.django_db
    def test_seasons_none(self, podcast):
        assert not get_podcast_seasons(podcast, 1)

    @pytest.mark.django_db
    def test_seasons(self, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast, season=1)
        EpisodeFactory.create_batch(2, podcast=podcast, season=2)
        dropdown = get_podcast_seasons(podcast, 1)
        assert dropdown.current
        assert dropdown.current.label == "Season 1"
        assert len(dropdown.items) == 2
        items = list(dropdown)
        assert items[0].label == "All Seasons"
        assert items[1].label == "Season 2"
