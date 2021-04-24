import pytest

from ..factories import AudioLogFactory
from ..models import AudioLog
from ..player import Player

pytestmark = pytest.mark.django_db


class TestPlayer:
    def test_start_episode(self, rf, user, episode):
        req = rf.get("/")
        req.session = {}
        req.user = user
        req.episode = episode
        player = Player(req)
        player.start_episode(episode)

        log = AudioLog.objects.get()

        assert log.episode == episode
        assert log.user == user
        assert log.updated
        assert log.current_time == 0
        assert not log.completed

        assert player.is_playing(episode)

    def test_start_episode_already_played(self, rf, user, episode):

        log = AudioLogFactory(episode=episode, user=user, current_time=500)

        req = rf.get("/")
        req.session = {}
        req.user = user
        req.episode = episode
        player = Player(req)
        player.start_episode(episode)

        log.refresh_from_db()

        assert log.episode == episode
        assert log.user == user
        assert log.updated
        assert log.current_time == 500
        assert not log.completed

        assert player.is_playing(episode)

    def test_stop_episode_empty(self, rf):
        req = rf.get("/")
        req.session = {}
        player = Player(req)
        assert player.stop_episode() is None

    def test_get_player_info_anonymous(self, rf, anonymous_user):

        req = rf.get("/")
        req.session = {}
        req.user = anonymous_user
        player = Player(req)
        assert player.get_player_info() == {}

    def test_get_player_info_user_empty(self, rf, user):

        req = rf.get("/")
        req.session = {}
        req.user = user
        player = Player(req)
        assert player.get_player_info() == {}

    def test_get_player_info(self, rf, user):

        log = AudioLogFactory(user=user, current_time=100)

        req = rf.get("/")
        req.session = {"player_episode": log.episode.id}
        req.user = user
        player = Player(req)

        assert player.get_player_info() == {
            "current_time": 100,
            "episode": log.episode,
        }

    def test_stop_episode_not_in_session(self, rf, user):

        AudioLogFactory(user=user)

        req = rf.get("/")
        req.session = {}
        req.user = user

        player = Player(req)

        assert player.stop_episode() is None

    def test_stop_episode_in_session(self, rf, user):

        log = AudioLogFactory(user=user)

        req = rf.get("/")
        req.session = {"player_episode": log.episode.id}
        req.user = user

        player = Player(req)

        assert player.stop_episode() == log.episode
        assert not player.is_playing(log.episode)

    def test_update_current_time(self, rf, user):

        log = AudioLogFactory(user=user, current_time=500)

        req = rf.get("/")

        req.session = {"player_episode": log.episode.id}
        req.user = user

        player = Player(req)
        player.update_current_time(600)

        log.refresh_from_db()
        assert log.current_time == 600
