import pytest
from django.template.context import RequestContext

from radiofeed.episodes.factories import create_audio_log
from radiofeed.episodes.middleware import Player
from radiofeed.episodes.templatetags.audio_player import audio_player


class TestAudioPlayer:
    @pytest.mark.django_db
    def test_is_empty(self, rf, user):
        req = rf.get("/")
        req.user = user
        req.session = {}
        req.player = Player(req)
        assert audio_player(RequestContext(req)) == {}

    @pytest.mark.django_db
    def test_is_playing(self, rf, user, episode):
        log = create_audio_log(episode=episode, user=user)

        req = rf.get("/")
        req.user = user
        req.session = {}

        req.player = Player(req)
        req.player.set(log.episode.id)

        assert audio_player(RequestContext(req)) == {
            "request": req,
            "audio_log": log,
            "is_playing": True,
        }
