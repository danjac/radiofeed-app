# Third Party Libraries
import pytest

# Local
from .. import views
from ..factories import EpisodeFactory

pytestmark = pytest.mark.django_db


class TestEpisodeList:
    def test_get(self, rf):
        EpisodeFactory.create_batch(3)
        response = views.episode_list(rf.get("/"))
        assert response.status_code == 200
        assert len(response.context_data["episodes"]) == 3


class TestEpisodeDetail:
    def test_get(self, rf, episode):
        response = views.episode_detail(rf.get("/"), episode.id, episode.slug)
        assert response.status_code == 200
        assert response.context_data["episode"] == episode
