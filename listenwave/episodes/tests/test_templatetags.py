import pytest

from listenwave.episodes.middleware import PlayerDetails
from listenwave.episodes.templatetags.episodes import audio_player, get_media_metadata
from listenwave.request import RequestContext


class TestGetMediaMetadata:
    @pytest.mark.django_db
    def test_get_media_metadata(self, rf, episode):
        req = rf.get("/")
        context = RequestContext(request=req)
        assert get_media_metadata(context, episode)


class TestAudioPlayer:
    @pytest.mark.django_db
    def test_close(self, rf, audio_log):
        req = rf.get("/")
        req.user = audio_log.user
        req.player = PlayerDetails(request=req)
        req.session = {req.player.session_id: audio_log.episode_id}

        context = RequestContext(request=req)

        dct = audio_player(context, audio_log, action="close")
        assert "audio_log" not in dct

    @pytest.mark.django_db
    def test_play(self, rf, audio_log):
        req = rf.get("/")
        req.user = audio_log.user

        context = RequestContext(request=req)

        dct = audio_player(context, audio_log, action="play")
        assert dct["audio_log"] == audio_log

    @pytest.mark.django_db
    def test_load(self, rf, audio_log):
        req = rf.get("/")
        req.user = audio_log.user
        req.player = PlayerDetails(request=req)
        req.session = {req.player.session_id: audio_log.episode_id}

        context = RequestContext(request=req)

        dct = audio_player(context, None, action="load")
        assert dct["audio_log"] == audio_log

    @pytest.mark.django_db
    def test_load_empty(self, rf, audio_log):
        req = rf.get("/")
        req.user = audio_log.user
        req.player = PlayerDetails(request=req)
        req.session = {}

        context = RequestContext(request=req)

        dct = audio_player(context, None, action="load")
        assert dct["audio_log"] is None

    @pytest.mark.django_db
    def test_load_user_not_authenticated(self, rf, audio_log, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        req.player = PlayerDetails(request=req)
        req.session = {}
        req.session = {req.player.session_id: audio_log.episode_id}

        context = RequestContext(request=req)

        dct = audio_player(context, None, action="load")
        assert dct["audio_log"] is None
