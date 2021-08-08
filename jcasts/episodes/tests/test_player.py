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

    def test_get_episode_if_none(self, player):
        assert player.get_episode() is None

    def test_get_episode_if_not_none(self, player, episode):
        player.set_episode(episode)
        assert player.get_episode() == episode.id

    def test_remove_episode_if_none(self, player):
        assert player.remove_episode() is None

    def test_remove_episode_if_not_none(self, player, episode):
        player.set_episode(episode)

        assert player.remove_episode() == episode.id
        assert player.get_episode() is None

    def test_is_playing_false(self, player, episode):
        assert not player.is_episode(episode)

    def test_is_playing_true(self, player, episode):
        player.set_episode(episode)
        assert player.is_episode(episode)
