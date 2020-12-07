# Third Party Libraries
import pytest

# Local
from ..factories import CategoryFactory, PodcastFactory
from ..models import Category, Podcast

pytestmark = pytest.mark.django_db


class TestCategoryManager:
    def test_search(self):
        CategoryFactory(name="testing")
        assert Category.objects.search("testing").count() == 1


class TestCategoryModel:
    def test_slug(self):
        category = Category(name="Testing")
        assert category.slug == "testing"


class TestPodcastManager:
    def test_search(self):
        PodcastFactory(title="testing")
        assert Podcast.objects.search("testing").count() == 1


class TestPodcastModel:
    def test_slug(self):
        podcast = Podcast(title="Testing")
        assert podcast.slug == "testing"

    def test_slug_if_title_empty(self):
        assert Podcast().slug == "podcast"
