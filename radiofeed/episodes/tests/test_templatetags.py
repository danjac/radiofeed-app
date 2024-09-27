import pytest
from django.template.context import RequestContext

from radiofeed.episodes.middleware import PlayerDetails
from radiofeed.episodes.templatetags.audio_player import (
    audio_player,
    audio_player_update,
    get_media_metadata,
)
from radiofeed.episodes.tests.factories import AudioLogFactory, EpisodeFactory
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestMediaMetadata:
    @pytest.mark.django_db
    def test_get_media_metadata(self, rf):
        episode = EpisodeFactory(
            podcast=PodcastFactory(cover_url="https://mysite.com/test.jpg")
        )
        data = get_media_metadata(RequestContext(rf.get("/")), episode)
        assert data["title"] == episode.title
        assert data["album"] == episode.podcast.title
        assert data["artist"] == episode.podcast.owner

        assert len(data["artwork"]) == 4

        assert data["artwork"][0]["src"].startswith(
            "http://testserver/covers/96/cover.webp"
        )
        assert data["artwork"][0]["sizes"] == "96x96"
        assert data["artwork"][0]["type"] == "image/webp"

    @pytest.mark.django_db
    def test_get_media_metadata_no_cover_url(self, rf):
        episode = EpisodeFactory(podcast=PodcastFactory(cover_url=""))
        data = get_media_metadata(RequestContext(rf.get("/")), episode)
        assert data["title"] == episode.title
        assert data["album"] == episode.podcast.title
        assert data["artist"] == episode.podcast.owner

        assert len(data["artwork"]) == 4

        assert (
            data["artwork"][0]["src"]
            == "http://testserver/static/img/placeholder-96.webp"
        )
        assert data["artwork"][0]["sizes"] == "96x96"
        assert data["artwork"][0]["type"] == "image/webp"


class TestAudioPlayerUpdate:
    @pytest.fixture
    def audio_log(self, user, episode):
        return AudioLogFactory(episode=episode, user=user)

    @pytest.fixture
    def req_context(self, rf):
        return RequestContext(rf.get("/"))

    @pytest.mark.django_db
    def test_start_player(self, audio_log, req_context):
        data = audio_player_update(req_context, "open", audio_log)
        assert data["hx_oob"] is True
        assert data["start_player"] is True
        assert data["audio_log"] == audio_log

    @pytest.mark.django_db
    def test_close_player(self, audio_log, req_context):
        data = audio_player_update(req_context, "close", audio_log)
        assert data["hx_oob"] is True
        assert "audio_log" not in data

    @pytest.mark.django_db
    def test_start_player_audio_log_none(self, req_context):
        data = audio_player_update(req_context, "open", None)
        assert data["hx_oob"] is True
        assert "audio_log" not in data


class TestAudioPlayer:
    @pytest.fixture
    def defaults(self):
        return {
            "is_playing": False,
            "start_player": False,
            "current_time": None,
            "episode": None,
        }

    @pytest.fixture
    def audio_log(self, user, episode):
        return AudioLogFactory(episode=episode, user=user)

    @pytest.mark.django_db
    def test_is_anonymous(self, rf, anonymous_user, defaults):
        req = rf.get("/")
        req.user = anonymous_user
        req.session = {}
        req.player = PlayerDetails(request=req)

        context = audio_player(RequestContext(req))

        assert context["audio_log"] is None

    @pytest.mark.django_db
    def test_is_empty(self, rf, user, defaults):
        req = rf.get("/")
        req.user = user
        req.session = {}
        req.player = PlayerDetails(request=req)
        context = audio_player(RequestContext(req))

        assert context["audio_log"] is None

    @pytest.mark.django_db
    def test_is_playing(self, rf, user, audio_log, defaults):
        req = rf.get("/")
        req.user = user
        req.session = {}

        req.player = PlayerDetails(request=req)
        req.player.set(audio_log.episode.pk)

        context = audio_player(RequestContext(req))
        assert context["audio_log"] == audio_log

    @pytest.mark.django_db
    def test_is_anonymous_is_playing(self, rf, anonymous_user, episode, defaults):
        req = rf.get("/")
        req.user = anonymous_user
        req.session = {}

        req.player = PlayerDetails(request=req)
        req.player.set(episode.pk)

        context = audio_player(RequestContext(req))
        assert context["audio_log"] is None
