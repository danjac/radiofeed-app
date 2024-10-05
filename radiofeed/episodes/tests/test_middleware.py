import pytest

from radiofeed.episodes.middleware import PlayerDetails, PlayerMiddleware
from radiofeed.episodes.tests.factories import AudioLogFactory


class TestPlayerMiddleware:
    def test_middleware(self, rf, get_response):
        req = rf.get("/")
        PlayerMiddleware(get_response)(req)
        assert req.player


class TestPlayerDetails:
    episode_id = 12345

    @pytest.fixture
    def req(self, rf):
        req = rf.get("/")
        req.session = {}
        return req

    @pytest.fixture
    def player(self, req):
        return PlayerDetails(request=req)

    def test_get_if_none(self, player):
        assert player.get() is None

    def test_get_if_not_none(self, player):
        player.set(self.episode_id)
        assert player.get() == self.episode_id

    def test_pop_if_none(self, player):
        assert player.pop() is None

    def test_pop_if_not_none(self, player):
        player.set(self.episode_id)

        assert player.pop() == self.episode_id
        assert player.get() is None

    def test_has_false(self, player):
        assert not player.has(self.episode_id)

    def test_has_true(self, player):
        player.set(self.episode_id)
        assert player.has(self.episode_id)

    @pytest.mark.django_db
    def test_audio_log_exists(self, user, req):
        audio_log = AudioLogFactory(user=user)
        req.user = user

        player = PlayerDetails(request=req)
        player.set(audio_log.episode_id)

        assert player.audio_log == audio_log

    @pytest.mark.django_db
    def test_audio_log_empty(self, user, req):
        req.user = user

        player = PlayerDetails(request=req)

        assert player.audio_log is None

    @pytest.mark.django_db
    def test_audio_log_anon_user(self, user, anonymous_user, req):
        audio_log = AudioLogFactory(user=user)
        req.user = anonymous_user

        player = PlayerDetails(request=req)
        player.set(audio_log.episode_id)

        assert player.audio_log is None

    @pytest.mark.django_db
    def test_audio_log_not_exists(self, user, req):
        req.user = user

        player = PlayerDetails(request=req)
        player.set(12345)

        assert player.audio_log is None
