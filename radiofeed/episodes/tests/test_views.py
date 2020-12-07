# Standard Library
import json

# Django
from django.urls import reverse

# Third Party Libraries
import pytest

# Local
from .. import views
from ..factories import EpisodeFactory

pytestmark = pytest.mark.django_db


class TestEpisodeList:
    def test_get(self, rf, anonymous_user):
        EpisodeFactory.create_batch(3)
        req = rf.get(reverse("episodes:episode_list"))
        req.user = anonymous_user
        resp = views.episode_list(req)
        assert resp.status_code == 200
        assert len(resp.context_data["episodes"]) == 3

    def test_search(self, rf, anonymous_user):
        EpisodeFactory.create_batch(3)
        EpisodeFactory(title="testing")
        req = rf.get(reverse("episodes:episode_list"), {"q": "testing"})
        req.user = anonymous_user
        resp = views.episode_list(req)
        assert resp.status_code == 200
        assert len(resp.context_data["episodes"]) == 1


class TestEpisodeDetail:
    def test_get(self, rf, episode):
        resp = views.episode_detail(
            rf.get(episode.get_absolute_url()), episode.id, episode.slug
        )
        assert resp.status_code == 200
        assert resp.context_data["episode"] == episode


class TestStartPlayer:
    def test_post(self, rf, episode):
        req = rf.post(reverse("episodes:start_player", args=[episode.id]))
        req.session = {}
        resp = views.start_player(req, episode.id)
        assert resp.status_code == 200
        assert req.session["player"] == {"episode": episode.id, "current_time": 0}


class TestStopPlayer:
    def test_post(self, rf, episode):
        req = rf.post(reverse("episodes:stop_player"))
        req.session = {"player": {"episode": episode.id, "current_time": 1000}}
        resp = views.stop_player(req)
        assert resp.status_code == 204
        assert req.session == {}


class TestUpdatePlayerTime:
    def test_post(self, rf, episode):
        req = rf.post(
            reverse("episodes:update_player_time"),
            data=json.dumps({"current_time": 1030}),
            content_type="application/json",
        )
        req.session = {"player": {"episode": episode.id, "current_time": 1000}}
        resp = views.update_player_time(req)
        assert resp.status_code == 204
        assert req.session == {"player": {"episode": episode.id, "current_time": 1030}}
