from jcasts.episodes.factories import AudioLogFactory
from jcasts.episodes.player import Player
from jcasts.episodes.templatetags.player import render_player


class TestRenderPlayer:
    def test_render_is_anonymous(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        assert render_player({"request": req}) == {"log": None}

    def test_render_is_empty(self, rf, user):
        req = rf.get("/")
        req.user = user
        req.session = {}
        req.player = Player(req)
        assert render_player({"request": req}) == {"log": None}

    def test_render_is_playing(self, rf, user, episode):
        log = AudioLogFactory(episode=episode, user=user)

        req = rf.get("/")
        req.user = user
        req.session = {}
        req.player = Player(req)
        req.player.add_episode(episode)

        assert render_player({"request": req}) == {"log": log}
