# Third Party Libraries
import pytest

# Local
from ..middleware import Player, PlayerSessionMiddleware

pytestmark = pytest.mark.django_db


class TestPlayer:
    def test_empty(self, rf):
        req = rf.get("/")
        req.session = {}
        player = Player(req)
        assert not player
        assert player.get_episode() is None
        assert player.get_current_time() == 0

    def test_not_empty(self, rf, episode):
        req = rf.get("/")
        req.session = {"player": {"episode": episode.id, "current_time": 1000}}
        player = Player(req)
        assert player
        assert player.get_episode() == episode
        assert player.get_current_time() == 1000

    def test_clear(self, rf, episode):
        req = rf.get("/")
        req.session = {"player": {"episode": episode.id, "current_time": 1000}}

        player = Player(req)
        assert player.get_current_time() == 1000
        current_episode = player.clear()

        assert current_episode == episode

        assert not player
        assert player.get_current_time() == 0

    def test_is_playing_true(self, rf, episode):
        req = rf.get("/")
        req.session = {"player": {"episode": episode.id, "current_time": 1000}}
        player = Player(req)
        assert player.is_playing(episode)

    def test_is_playing_false(self, rf, episode):
        req = rf.get("/")
        req.session = {"player": {"episode": 12345, "current_time": 1000}}
        player = Player(req)
        assert not player.is_playing(episode)

    def test_is_playing_empty(self, rf, episode):
        req = rf.get("/")
        req.session = {}
        player = Player(req)
        assert not player.is_playing(episode)


class TestPlayerSessionMiddleware:
    def test_player_in_request(self, rf, get_response):
        req = rf.get("/")
        req.session = {}
        PlayerSessionMiddleware(get_response)(req)
        assert hasattr(req, "player")
