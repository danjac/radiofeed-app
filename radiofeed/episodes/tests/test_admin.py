import pytest
from django.contrib.admin.sites import AdminSite

from radiofeed.episodes.admin import EpisodeAdmin
from radiofeed.episodes.models import Episode
from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestEpisodeAdmin:
    @pytest.fixture(scope="class")
    def admin(self):
        return EpisodeAdmin(Episode, AdminSite())

    @pytest.mark.django_db
    def test_episode_title(self, admin):
        episode = EpisodeFactory(title="testing")
        assert admin.episode_title(episode) == "testing"

    @pytest.mark.django_db
    def test_podcast_title(self, admin):
        episode = EpisodeFactory(podcast=PodcastFactory(title="testing"))
        assert admin.podcast_title(episode) == "testing"

    @pytest.mark.django_db
    def test_get_ordering_no_search_term(self, admin, rf):
        ordering = admin.get_ordering(rf.get("/"))
        assert ordering == ["-id"]

    @pytest.mark.django_db
    def test_get_ordering_search_term(self, admin, rf):
        ordering = admin.get_ordering(rf.get("/", {"q": "test"}))
        assert ordering == []

    @pytest.mark.django_db
    def test_get_search_results_no_search_term(self, rf, admin):
        EpisodeFactory.create_batch(3)
        qs, _ = admin.get_search_results(rf.get("/"), Episode.objects.all(), "")
        assert qs.count() == 3

    @pytest.mark.django_db
    def test_get_search_results(self, rf, admin):
        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory(title="testing python")

        qs, _ = admin.get_search_results(
            rf.get("/"), Episode.objects.all(), "testing python"
        )
        assert qs.count() == 1
        assert qs.first() == episode
