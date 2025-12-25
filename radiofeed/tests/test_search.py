import pytest

from radiofeed.episodes.models import AudioLog
from radiofeed.episodes.tests.factories import AudioLogFactory, EpisodeFactory
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory
from radiofeed.search import search_queryset


class TestSearchQueryset:
    @pytest.mark.django_db
    def test_empty_value(self):
        result = search_queryset(Podcast.objects.all(), "", "search_vector")
        assert result.count() == 0

    @pytest.mark.django_db
    def test_search_found(self):
        podcast_1 = PodcastFactory(title="Learn Python Programming")
        podcast_2 = PodcastFactory(title="Advanced Python Techniques")

        PodcastFactory(title="JavaScript Basics")
        result = search_queryset(
            Podcast.objects.all(),
            "Python",
            "search_vector",
        )

        assert result.count() == 2

        assert podcast_1 in result
        assert podcast_2 in result

    @pytest.mark.django_db
    def test_multiple_joined_fields(self):
        audio_log_1 = AudioLogFactory(
            episode=EpisodeFactory(
                title="This is a test transcript about Django.",
                podcast__title="Django Podcast",
            )
        )
        audio_log_2 = AudioLogFactory(
            episode=EpisodeFactory(
                title="Django for beginners.",
                podcast__title="Web Dev Podcast",
            )
        )
        AudioLogFactory(
            episode=EpisodeFactory(
                title="Learning Flask framework.",
                podcast__title="Flask Podcast",
            )
        )

        result = search_queryset(
            AudioLog.objects.all(),
            "Django",
            "episode__search_vector",
            "episode__podcast__search_vector",
        )
        assert result.count() == 2
        assert audio_log_1 in result
        assert audio_log_2 in result
