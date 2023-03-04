from __future__ import annotations

from django.template.context import RequestContext

from radiofeed.episodes.factories import create_audio_log
from radiofeed.episodes.templatetags.audio_player import audio_player


class TestAudioPlayer:
    def test_is_empty(self, rf, user):
        req = rf.get("/")
        req.user = user
        req.session = {}
        assert audio_player(RequestContext(req)) == {}

    def test_is_playing(self, rf, user, episode):
        log = create_audio_log(episode=episode, user=user, is_playing=True)

        req = rf.get("/")
        req.user = user

        assert audio_player(RequestContext(req)) == {
            "request": req,
            "episode": log.episode,
            "current_time": log.current_time,
            "is_playing": True,
        }

    def test_is_not_playing(self, rf, user, episode):
        create_audio_log(episode=episode, user=user, is_playing=False)

        req = rf.get("/")
        req.user = user

        assert audio_player(RequestContext(req)) == {}
