# Third Party Libraries
import pytest

# Local
from ..factories import BookmarkFactory, EpisodeFactory
from ..models import Bookmark, Episode

pytestmark = pytest.mark.django_db


class TestEpisodeManager:
    def test_search(self):
        EpisodeFactory(title="testing")
        assert Episode.objects.search("testing").count() == 1


class TestEpisodeModel:
    def test_slug(self):
        episode = Episode(title="Testing")
        assert episode.slug == "testing"

    def test_slug_if_title_empty(self):
        assert Episode().slug == "episode"

    def test_get_duration_in_seconds_if_empty(self):
        assert Episode().get_duration_in_seconds() == 0
        assert Episode(duration="").get_duration_in_seconds() == 0

    def test_duration_in_seconds_if_non_numeric(self):
        assert Episode(duration="NaN").get_duration_in_seconds() == 0

    def test_duration_in_seconds_if_seconds_only(self):
        assert Episode(duration="60").get_duration_in_seconds() == 60

    def test_duration_in_seconds_if_minutes_and_seconds(self):
        assert Episode(duration="2:30").get_duration_in_seconds() == 150

    def test_duration_in_seconds_if_hours_minutes_and_seconds(self):
        assert Episode(duration="2:30:30").get_duration_in_seconds() == 9030


class TestBookmarkManager:
    def test_search(self):
        episode = EpisodeFactory(title="testing")
        BookmarkFactory(episode=episode)
        assert Bookmark.objects.search("testing").count() == 1
