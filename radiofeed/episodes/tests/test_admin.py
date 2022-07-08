from __future__ import annotations

import pytest

from django.contrib.admin.sites import AdminSite

from radiofeed.episodes.admin import EpisodeAdmin
from radiofeed.episodes.factories import EpisodeFactory
from radiofeed.episodes.models import Episode


class TestEpisodeAdmin:
    @pytest.fixture(scope="class")
    def admin(self):
        return EpisodeAdmin(Episode, AdminSite())

    def test_episode_title(self, db, admin):
        episode = EpisodeFactory(title="testing")
        assert admin.episode_title(episode) == "testing"

    def test_podcast_title(self, db, admin):
        episode = EpisodeFactory(podcast__title="testing")
        assert admin.podcast_title(episode) == "testing"

    def test_get_ordering_no_search_term(self, admin, rf):
        ordering = admin.get_ordering(rf.get("/"))
        assert ordering == ["-id"]

    def test_get_ordering_search_term(self, admin, rf):
        ordering = admin.get_ordering(rf.get("/", {"q": "test"}))
        assert ordering == []

    def test_get_search_results_no_search_term(self, rf, db, admin):
        EpisodeFactory.create_batch(3)
        qs, _ = admin.get_search_results(rf.get("/"), Episode.objects.all(), "")
        assert qs.count() == 3

    def test_get_search_results(self, rf, db, admin):
        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory(title="testing python")

        qs, _ = admin.get_search_results(rf.get("/"), Episode.objects.all(), "testing python")
        assert qs.count() == 1
        assert qs.first() == episode
