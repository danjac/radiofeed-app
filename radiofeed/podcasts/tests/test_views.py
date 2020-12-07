# Third Party Libraries
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
        response = views.podcast_list(rf.get("/"))
        assert response.status_code == 200
        assert len(response.context_data["podcasts"]) == 3


class TestPodcastDetail:
    def test_get(self, rf, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        response = views.podcast_detail(rf.get("/"), podcast.id, podcast.slug)
        assert response.status_code == 200
        assert response.context_data["podcast"] == podcast
        assert len(response.context_data["episodes"]) == 3
