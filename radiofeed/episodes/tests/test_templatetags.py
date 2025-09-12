import pytest
from django.template import Context

from radiofeed.episodes.templatetags.audio_player import get_media_metadata


class TestGetMediaMetadata:
    @pytest.mark.django_db
    def test_get_media_metadata(self, rf, episode):
        req = rf.get("/")
        context = Context({"request": req})
        assert get_media_metadata(context, episode)

    @pytest.mark.django_db
    def test_request_missing(self, episode):
        context = Context()
        assert get_media_metadata(context, episode) == {}
