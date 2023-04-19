from __future__ import annotations

import pytest
from django.contrib.admin.sites import AdminSite

from radiofeed.episodes.admin import EpisodeAdmin
from radiofeed.episodes.factories import create_episode
from radiofeed.episodes.models import Episode
from radiofeed.factories import create_batch
from radiofeed.podcasts.factories import create_podcast


class TestEpisodeAdmin:
    @pytest.fixture(scope="class")
    def admin(self):
        return EpisodeAdmin(Episode, AdminSite())

    def test_episode_title(self, db, admin):
        episode = create_episode(title="testing")
        assert admin.episode_title(episode) == "testing"

    def test_podcast_title(self, db, admin):
        episode = create_episode(podcast=create_podcast(title="testing"))
        assert admin.podcast_title(episode) == "testing"

    def test_get_ordering_no_search_term(self, admin, rf):
        ordering = admin.get_ordering(rf.get("/"))
        assert ordering == ["-id"]

    def test_get_ordering_search_term(self, admin, rf):
        ordering = admin.get_ordering(rf.get("/", {"q": "test"}))
        assert ordering == []

    def test_get_search_results_no_search_term(self, rf, db, admin):
        create_batch(create_episode, 3)
        qs, _ = admin.get_search_results(rf.get("/"), Episode.objects.all(), "")
        assert qs.count() == 3

    def test_get_search_results(self, rf, db, admin):
        create_batch(create_episode, 3)

        episode = create_episode(title="testing python")

        qs, _ = admin.get_search_results(
            rf.get("/"), Episode.objects.all(), "testing python"
        )
        assert qs.count() == 1
        assert qs.first() == episode
