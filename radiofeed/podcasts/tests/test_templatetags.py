import pytest

from ..factories import PodcastFactory
from ..models import _cover_image_placeholder
from ..templatetags.podcasts import (
    cover_image,
    get_promoted_podcasts,
    get_recently_added_podcasts,
)

pytestmark = pytest.mark.django_db


class TestGetRecentlyAddedPodcasts:
    def test_get_podcasts(self):
        PodcastFactory.create_batch(3, cover_image="test.jpg")
        podcasts = get_recently_added_podcasts(2)
        assert len(podcasts) == 2


class TestGetPromotedPodcasts:
    def test_get_podcasts(self):
        PodcastFactory(cover_image="test.jpg", promoted=False)
        PodcastFactory.create_batch(2, cover_image="test.jpg", promoted=True)
        podcasts = get_promoted_podcasts(3)
        assert len(podcasts) == 2


class TestCoverImage:
    def test_lazy_cover_image_provided(self, podcast):
        dct = cover_image(podcast, cover_image=_cover_image_placeholder, lazy=True)
        assert dct["cover_image"] is not None
        assert dct["podcast"] == podcast
        assert dct["lazy"] is False

    def test_lazy_cover_image_not_provided(self, podcast):
        dct = cover_image(podcast, cover_image=None, lazy=True)
        assert dct["cover_image"] is None
        assert dct["podcast"] == podcast
        assert dct["lazy"] is True

    def test_not_lazy(self):
        podcast = PodcastFactory(cover_image="test.jpg")
        dct = cover_image(podcast, cover_image=None, lazy=False)
        assert dct["cover_image"] is not None
        assert dct["podcast"] == podcast
        assert dct["lazy"] is False
