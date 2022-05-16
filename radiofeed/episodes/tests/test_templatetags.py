from radiofeed.episodes.factories import AudioLogFactory
from radiofeed.episodes.middleware import Player
from radiofeed.episodes.templatetags.player import audio_player


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
            "request": req,
            "episode": log.episode,
            "current_time": log.current_time,
            "is_playing": True,
        }
