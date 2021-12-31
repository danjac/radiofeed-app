from jcasts.episodes.factories import AudioLogFactory
from jcasts.episodes.middleware import Player
from jcasts.episodes.templatetags.player import audio_player


class TestRenderPlayer:
    def test_is_anonymous(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        assert audio_player({"request": req}) == {}

    def test_is_empty(self, rf, user):
        req = rf.get("/")
        req.user = user
        req.session = {}
        req.player = Player(req)
        assert audio_player({"request": req}) == {}

    def test_is_playing(self, rf, user, episode):
        log = AudioLogFactory(episode=episode, user=user)

        req = rf.get("/")
        req.user = user
        req.session = {Player.session_key: episode.id}
        req.player = Player(req)

        assert audio_player({"request": req}) == {
            "log": log,
            "episode": log.episode,
            "is_playing": True,
        }
