import pytest
from django.template.context import RequestContext

from radiofeed.episodes.middleware import PlayerDetails
from radiofeed.episodes.templatetags.audio_player import (
    audio_player,
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

        assert len(data["artwork"]) == 5

        assert data["artwork"][0]["src"].startswith(
            "http://testserver/covers/96/cover.webp"
        )
        assert data["artwork"][0]["sizes"] == "96x96"
        assert data["artwork"][0]["type"] == "image/webp"

    @pytest.mark.django_db
    def test_get_media_metadata_no_cover_url(self, rf):
        episode = EpisodeFactory(podcast=PodcastFactory(cover_url=None))
        data = get_media_metadata(RequestContext(rf.get("/")), episode)
        assert data["title"] == episode.title
        assert data["album"] == episode.podcast.title
        assert data["artist"] == episode.podcast.owner

        assert len(data["artwork"]) == 5

        assert (
            data["artwork"][0]["src"]
            == "http://testserver/static/img/placeholder-96.webp"
        )
        assert data["artwork"][0]["sizes"] == "96x96"
        assert data["artwork"][0]["type"] == "image/webp"


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
        req.player = PlayerDetails(req)
        assert audio_player(RequestContext(req)) == {
            **defaults,
            "request": req,
        }

    @pytest.mark.django_db
    def test_is_empty(self, rf, user, defaults):
        req = rf.get("/")
        req.user = user
        req.session = {}
        req.player = PlayerDetails(req)
        assert audio_player(RequestContext(req)) == defaults | {"request": req}

    @pytest.mark.django_db
    def test_is_playing(self, rf, user, audio_log, defaults):
        req = rf.get("/")
        req.user = user
        req.session = {}

        req.player = PlayerDetails(req)
        req.player.set(audio_log.episode.pk)

        assert audio_player(RequestContext(req)) == {
            **defaults,
            "request": req,
            "episode": audio_log.episode,
            "is_playing": True,
            "current_time": 1000,
        }

    @pytest.mark.django_db
    def test_is_anonymous_is_playing(self, rf, anonymous_user, episode, defaults):
        req = rf.get("/")
        req.user = anonymous_user
        req.session = {}

        req.player = PlayerDetails(req)
        req.player.set(episode.pk)

        assert audio_player(RequestContext(req)) == defaults | {"request": req}
