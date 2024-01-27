import pytest

from radiofeed.episodes.middleware import Player, PlayerMiddleware


class TestPlayerMiddleware:
    def test_middleware(self, rf, get_response):
        req = rf.get("/")
        PlayerMiddleware(get_response)(req)
        assert req.player


class TestPlayer:
    episode_id = 12345

    @pytest.fixture()
    def req(self, rf):
        req = rf.get("/")
        req.session = {}
        return req

    @pytest.fixture()
    def player(self, req):
        return Player(req)

    def test_get_if_none(self, player):
        assert player.get() is None

    def test_set_current_time(self, player):
        player.set_current_time(10)
        assert player.get_current_time() == 10

    def test_set_current_time_invalid(self, player):
        player.set_current_time("argh")
        assert player.get_current_time() == 0

    def test_get_if_not_none(self, player):
        player.set(self.episode_id, 10)
        assert player.get() == self.episode_id
        assert player.get_current_time() == 10

    def test_pop_if_none(self, player):
        assert player.pop() is None
        assert player.get_current_time() == 0

    def test_pop_if_not_none(self, player):
        player.set(self.episode_id, 10)
        player.set_current_time(10)

        assert player.pop() == self.episode_id
        assert player.get() is None
        assert player.get_current_time() == 0

    def test_has_false(self, player):
        assert not player.has(self.episode_id)

    def test_has_true(self, player):
        player.set(self.episode_id, 10)
        assert player.has(self.episode_id)
