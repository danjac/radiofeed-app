import pytest

from listenwave.episodes.models import AudioLog
from listenwave.episodes.tests.factories import AudioLogFactory
from listenwave.podcasts.models import Podcast
from listenwave.podcasts.tests.factories import PodcastFactory
from listenwave.search import search_queryset


class TestSearchQueryset:
    @pytest.mark.django_db
    def test_search(self):
        PodcastFactory(title="testing")
        podcasts = search_queryset(
            Podcast.objects.all(),
            "testing",
            "search_vector",
        )
        assert podcasts.count() == 1
        assert podcasts.get().rank > 0

    @pytest.mark.django_db
    def test_missing_fields(self):
        with pytest.raises(
            ValueError,
            match="At least one search vector field must be provided",
        ):
            search_queryset(Podcast.objects.all(), "testing")

    @pytest.mark.django_db
    def test_empty_search(self):
        PodcastFactory(title="testing")
        assert search_queryset(Podcast.objects.all(), "", "search_vector").count() == 0

    @pytest.mark.django_db
    def test_multiple_fields(self):
        AudioLogFactory(
            episode__title="unique episode",
            episode__podcast__title="common podcast",
        )
        assert (
            search_queryset(
                AudioLog.objects.all(),
                "unique",
                "episode__search_vector",
                "episode__podcast__search_vector",
            ).count()
            == 1
        )
        assert (
            search_queryset(
                AudioLog.objects.all(),
                "common",
                "episode__search_vector",
                "episode__podcast__search_vector",
            ).count()
            == 1
        )
