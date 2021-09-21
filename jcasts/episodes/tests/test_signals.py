from jcasts.episodes.factories import AudioLogFactory
from jcasts.episodes.middleware import Player
from jcasts.episodes.signals import get_last_player_episode


class TestGetLastPlayerEpisode:
    def test_is_player_episode(self, rf, user):
        log = AudioLogFactory(user=user, is_playing=True)

        req = rf.get("/")
        req.session = {}
        req.user = user
        req.player = Player(req)

        get_last_player_episode(None, req)

        assert req.player.has(log.episode_id)

    def test_is_not_playing(self, rf, user):
        log = AudioLogFactory(user=user, is_playing=False)

        req = rf.get("/")
        req.session = {}
        req.user = user
        req.player = Player(req)

        get_last_player_episode(None, req)

        assert not req.player.has(log.episode_id)
