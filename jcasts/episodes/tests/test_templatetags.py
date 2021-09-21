from jcasts.episodes.factories import AudioLogFactory
from jcasts.episodes.templatetags.player import audio_player


class TestRenderPlayer:
    def test_is_anonymous(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        assert audio_player({"request": req}) == {}

    def test_is_empty(self, rf, user):
        req = rf.get("/")
        req.user = user
        assert audio_player({"request": req}) == {"log": None}

    def test_is_not_playing(self, rf, user, episode):
        AudioLogFactory(episode=episode, user=user, is_playing=False)

        req = rf.get("/")
        req.user = user

        assert audio_player({"request": req}) == {"log": None}

    def test_is_playing(self, rf, user, episode):
        log = AudioLogFactory(episode=episode, user=user, is_playing=True)

        req = rf.get("/")
        req.user = user

        assert audio_player({"request": req}) == {"log": log}
