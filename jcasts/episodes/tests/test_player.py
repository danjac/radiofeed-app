import pytest

from jcasts.episodes.player import Player


class TestPlayer:
    @pytest.fixture
    def req(self, rf):
        req = rf.get("/")
        req.session = {}
        return req

    @pytest.fixture
    def player(self, req):
        return Player(req)

    def test_add_episode(self, req, player, episode):
        player.add_episode(episode)
        assert player.is_playing(episode)
        assert player.get_episode() == episode.id

    def test_is_playing_empty(self, req, player, episode):
        assert not player.is_playing(episode)
        assert player.get_episode() is None

    def test_remove_episode(self, req, player, episode):
        player.add_episode(episode)
        episode_id = player.remove_episode()
        assert not player.is_playing(episode)
        assert episode_id == episode.id

    def test_remove_episode_empty(self, req, player):
        assert player.remove_episode() is None
