import pytest
from django.template.context import RequestContext

from radiofeed.episodes.middleware import Player
from radiofeed.episodes.templatetags.audio_player import (
    audio_player,
    get_media_metadata,
)
from radiofeed.episodes.tests.factories import create_audio_log, create_episode
from radiofeed.podcasts.tests.factories import create_podcast
from radiofeed.template import get_placeholder_cover_url


class TestMediaMetadata:
    @pytest.mark.django_db()
    def test_get_media_metadata(self, rf):
        episode = create_episode(
            podcast=create_podcast(cover_url="https://mysite.com/test.jpg")
        )
        data = get_media_metadata(RequestContext(rf.get("/")), episode)
        assert data["title"] == episode.title
        assert data["album"] == episode.podcast.title
        assert data["artist"] == episode.podcast.owner

        assert len(data["artwork"]) == 3

        assert data["artwork"][0]["src"].startswith(
            "http://testserver/covers/100/cover.webp"
        )
        assert data["artwork"][0]["sizes"] == "100x100"
        assert data["artwork"][0]["type"] == "image/webp"

    @pytest.mark.django_db()
    def test_get_media_metadata_no_cover_url(self, rf):
        get_placeholder_cover_url.cache_clear()

        episode = create_episode(podcast=create_podcast(cover_url=None))
        data = get_media_metadata(RequestContext(rf.get("/")), episode)
        assert data["title"] == episode.title
        assert data["album"] == episode.podcast.title
        assert data["artist"] == episode.podcast.owner

        assert len(data["artwork"]) == 3

        assert (
            data["artwork"][0]["src"]
            == "http://testserver/static/img/placeholder-100.webp"
        )
        assert data["artwork"][0]["sizes"] == "100x100"
        assert data["artwork"][0]["type"] == "image/webp"


class TestAudioPlayer:
    @pytest.fixture()
    def defaults(self):
        return {
            "is_playing": False,
            "audio_log": None,
        }

    @pytest.mark.django_db()
    def test_is_anonymous(self, rf, anonymous_user, defaults):
        req = rf.get("/")
        req.user = anonymous_user
        req.session = {}
        req.player = Player(req)
        assert audio_player(RequestContext(req)) == {
            **defaults,
            "request": req,
            "user": req.user,
        }

    @pytest.mark.django_db()
    def test_is_empty(self, rf, user, defaults):
        req = rf.get("/")
        req.user = user
        req.session = {}
        req.player = Player(req)
        assert audio_player(RequestContext(req)) == {
            **defaults,
            "request": req,
            "user": req.user,
        }

    @pytest.mark.django_db()
    def test_is_playing(self, rf, user, episode, defaults):
        log = create_audio_log(episode=episode, user=user)

        req = rf.get("/")
        req.user = user
        req.session = {}

        req.player = Player(req)
        req.player.set(log.episode.id)

        assert audio_player(RequestContext(req)) == {
            **defaults,
            "request": req,
            "user": req.user,
            "audio_log": log,
            "is_playing": True,
        }
