import pytest
from django.contrib.sites.models import Site
from django.template import TemplateSyntaxError

from simplecasts.http.request import RequestContext
from simplecasts.middleware.player import PlayerDetails
from simplecasts.templatetags import (
    audio_player,
    cookie_banner,
    format_duration,
    fragment,
    get_media_metadata,
)


@pytest.fixture
def req(rf, anonymous_user):
    req = rf.get("/")
    req.user = anonymous_user
    req.htmx = False
    req.site = Site.objects.get_current()
    return req


@pytest.fixture
def auth_req(req, user):
    req.user = user
    return req


class TestBlockinclude:
    def test_render_no_template_obj(self, mocker):
        context = mocker.Mock()
        context.template = None
        with pytest.raises(TemplateSyntaxError):
            fragment(context, "header.html#title", "test")


class TestCookieBanner:
    def test_not_accepted(self, rf):
        req = rf.get("/")
        req.COOKIES = {}
        context = RequestContext(request=req)
        assert cookie_banner(context)["cookies_accepted"] is False

    def test_accepted(self, rf):
        req = rf.get("/")
        req.COOKIES = {"accept-cookies": True}
        context = RequestContext(request=req)
        assert cookie_banner(context)["cookies_accepted"] is True


# =============================================================================
# Episode Template Tags
# =============================================================================


class TestFormatDuration:
    @pytest.mark.parametrize(
        ("duration", "expected"),
        [
            pytest.param(0, "", id="zero"),
            pytest.param(30, "", id="30 seconds"),
            pytest.param(60, "1\xa0minute", id="1 minute"),
            pytest.param(61, "1\xa0minute", id="just over 1 minute"),
            pytest.param(90, "1\xa0minute", id="1 minute 30 seconds"),
            pytest.param(540, "9\xa0minutes", id="9 minutes"),
            pytest.param(2400, "40\xa0minutes", id="40 minutes"),
            pytest.param(3600, "1\xa0hour", id="1 hour"),
            pytest.param(9000, "2\xa0hours, 30\xa0minutes", id="2 hours 30 minutes"),
        ],
    )
    def test_format_duration(self, duration, expected):
        assert format_duration(duration) == expected


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
