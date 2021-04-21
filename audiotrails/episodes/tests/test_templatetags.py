import pytest

from ..factories import AudioLogFactory
from ..templatetags.player import get_player

pytestmark = pytest.mark.django_db


class TestGetPlayer:
    def test_anonymous(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        req.session = {}
        assert get_player({"request": req}) == {}

    def test_player_not_loaded(self, rf, user):
        req = rf.get("/")
        req.user = user
        req.session = {}
        assert get_player({"request": req}) == {}

    def test_player_loaded(self, rf, user, episode):
        AudioLogFactory(user=user, episode=episode, current_time=300)
        req = rf.get("/")
        req.user = user
        req.session = {"player_episode": episode.id}
        assert get_player({"request": req}) == {"episode": episode, "current_time": 300}
