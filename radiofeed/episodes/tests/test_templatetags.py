from __future__ import annotations

from django.template.context import RequestContext

from radiofeed.episodes.factories import AudioLogFactory
from radiofeed.episodes.player import Player
from radiofeed.episodes.templatetags.audio_player import audio_player


class TestAudioPlayer:
    def test_is_empty(self, rf, user):
        req = rf.get("/")
        req.user = user
        req.session = {}
        req.player = Player(req)
        assert audio_player(RequestContext(req)) == {}

    def test_is_playing(self, rf, user, episode):
        log = AudioLogFactory(episode=episode, user=user)

        req = rf.get("/")
        req.user = user
        req.session = {Player.session_key: episode.id}
        req.player = Player(req)

        assert audio_player(RequestContext(req)) == {
            "request": req,
            "episode": log.episode,
            "current_time": log.current_time,
            "is_playing": True,
        }
