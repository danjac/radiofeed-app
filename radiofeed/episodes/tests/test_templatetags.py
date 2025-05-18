import pytest
from django.template.context import Context

from radiofeed.episodes.middleware import PlayerDetails
from radiofeed.episodes.templatetags.audio_player import audio_player
from radiofeed.episodes.tests.factories import AudioLogFactory


class TestAudioPlayer:
    @pytest.mark.django_db
    def test_audio_player_play_action(self, rf):
        audio_log = AudioLogFactory()
        req = rf.get("/")
        req.user = audio_log.user

        dct = audio_player(Context({"request": req}), audio_log, action="play")
        assert dct["audio_log"] == audio_log
        assert dct["request"] == req
        assert dct["action"] == "play"

    @pytest.mark.django_db
    def test_audio_player_close_action(self, rf):
        audio_log = AudioLogFactory()
        req = rf.get("/")
        req.user = audio_log.user

        dct = audio_player(Context({"request": req}), audio_log, action="close")
        assert "audio_log" not in dct
        assert dct["request"] == req
        assert dct["action"] == "close"

    @pytest.mark.django_db
    def test_audio_player_loaded(self, rf):
        audio_log = AudioLogFactory()
        req = rf.get("/")
        req.session = {}
        req.player = PlayerDetails(request=req)
        req.player.set(audio_log.episode.pk)
        req.user = audio_log.user

        dct = audio_player(Context({"request": req}))
        assert dct["audio_log"] == audio_log
        assert dct["request"] == req
        assert dct["action"] == "load"

    @pytest.mark.django_db
    def test_audio_player_not_loaded(self, rf, user):
        req = rf.get("/")
        req.session = {}
        req.player = PlayerDetails(request=req)
        req.user = user

        dct = audio_player(Context({"request": req}))
        assert "audio_log" not in dct
        assert dct["request"] == req
        assert dct["action"] == "load"

    @pytest.mark.django_db
    def test_audio_player_anonymous(self, rf, anonymous_user):
        req = rf.get("/")
        req.session = {}
        req.player = PlayerDetails(request=req)
        req.user = anonymous_user

        dct = audio_player(Context({"request": req}))
        assert "audio_log" not in dct
        assert dct["request"] == req
        assert dct["action"] == "load"
