# Third Party Libraries
import pytest

# Local
from ..models import Podcast

pytestmark = pytest.mark.django_db


class TestPodcastModel:
    def test_slug(self):
        podcast = Podcast(title="Testing")
        assert podcast.slug == "testing"

    def test_slug_if_title_empty(self):
        assert Podcast().slug == "podcast"
