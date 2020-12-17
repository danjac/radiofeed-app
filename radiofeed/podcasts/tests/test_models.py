# Third Party Libraries
import pytest

# Local
from ..factories import CategoryFactory, PodcastFactory, SubscriptionFactory
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

    def test_with_subscription_count(self):
        subbed_1 = PodcastFactory()
        subbed_2 = PodcastFactory()
        unsubbed = PodcastFactory()

        SubscriptionFactory(podcast=subbed_1)
        SubscriptionFactory(podcast=subbed_1)
        SubscriptionFactory(podcast=subbed_2)

        podcasts = Podcast.objects.with_subscription_count().order_by(
            "-subscription_count"
        )

        assert podcasts[0].id == subbed_1.id
        assert podcasts[1].id == subbed_2.id
        assert podcasts[2].id == unsubbed.id

        assert podcasts[0].subscription_count == 2
        assert podcasts[1].subscription_count == 1
        assert podcasts[2].subscription_count == 0


class TestPodcastModel:
    def test_slug(self):
        podcast = Podcast(title="Testing")
        assert podcast.slug == "testing"

    def test_slug_if_title_empty(self):
        assert Podcast().slug == "podcast"
