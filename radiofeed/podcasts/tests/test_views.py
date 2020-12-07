# Third Party Libraries
# Django
from django.urls import reverse

import pytest

# RadioFeed
from radiofeed.episodes.factories import EpisodeFactory

# Local
from .. import views
from ..factories import PodcastFactory

pytestmark = pytest.mark.django_db


class TestPodcastList:
    def test_get(self, rf):
        PodcastFactory.create_batch(3)
        resp = views.podcast_list(rf.get(reverse("podcasts:podcast_list")))
        assert resp.status_code == 200
        assert len(resp.context_data["podcasts"]) == 3


class TestPodcastDetail:
    def test_get(self, rf, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        resp = views.podcast_detail(
            rf.get(podcast.get_absolute_url()), podcast.id, podcast.slug
        )
        assert resp.status_code == 200
        assert resp.context_data["podcast"] == podcast
        assert len(resp.context_data["episodes"]) == 3
