import pytest
from django.template.context import RequestContext

from radiofeed.episodes.templatetags.audio_player import get_media_metadata
from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestMediaMetadata:
    @pytest.mark.django_db
    def test_get_media_metadata(self, rf):
        episode = EpisodeFactory(
            podcast=PodcastFactory(cover_url="https://mysite.com/test.jpg")
        )
        data = get_media_metadata(RequestContext(rf.get("/")), episode)
        assert data["title"] == episode.cleaned_title
        assert data["album"] == episode.podcast.cleaned_title
        assert data["artist"] == episode.podcast.cleaned_title

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

        assert data["title"] == episode.cleaned_title
        assert data["album"] == episode.podcast.cleaned_title
        assert data["artist"] == episode.podcast.cleaned_title

        assert len(data["artwork"]) == 4

        assert (
            data["artwork"][0]["src"]
            == "http://testserver/static/img/placeholder-96.webp"
        )
        assert data["artwork"][0]["sizes"] == "96x96"
        assert data["artwork"][0]["type"] == "image/webp"
