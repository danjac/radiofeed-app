# Third Party Libraries
import pytest

# Local
from ..models import Episode

pytestmark = pytest.mark.django_db


class TestPodcastModel:
    def test_slug(self):
        episode = Episode(title="Testing")
        assert episode.slug == "testing"

    def test_slug_if_title_empty(self):
        assert Episode().slug == "episode"
