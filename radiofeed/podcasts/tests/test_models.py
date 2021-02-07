# Third Party Libraries
import pytest

# RadioFeed
from radiofeed.episodes.factories import AudioLogFactory, FavoriteFactory

# Local
from ..factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from ..models import Category, Podcast, Recommendation

pytestmark = pytest.mark.django_db


class TestRecommendationManager:
    def test_for_user(self, user):

        subscribed = SubscriptionFactory(user=user).podcast
        favorited = FavoriteFactory(user=user).episode.podcast
        listened = AudioLogFactory(user=user).episode.podcast

        received = RecommendationFactory(
            podcast=SubscriptionFactory(user=user).podcast
        ).recommended
        user.recommended_podcasts.add(received)

        first = RecommendationFactory(podcast=subscribed).recommended
        second = RecommendationFactory(podcast=favorited).recommended
        third = RecommendationFactory(podcast=listened).recommended

        # already received

        # not connected
        RecommendationFactory()

        # already subscribed, listened to or favorited
        RecommendationFactory(recommended=subscribed)
        RecommendationFactory(recommended=favorited)
        RecommendationFactory(recommended=listened)

        recommended = [r.recommended for r in Recommendation.objects.for_user(user)]

        assert len(recommended) == 3

        assert first in recommended
        assert second in recommended
        assert third in recommended


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
        subscribed_1 = PodcastFactory()
        subscribed_2 = PodcastFactory()
        unsubscribed = PodcastFactory()

        SubscriptionFactory(podcast=subscribed_1)
        SubscriptionFactory(podcast=subscribed_1)
        SubscriptionFactory(podcast=subscribed_2)

        podcasts = Podcast.objects.with_subscription_count().order_by(
            "-subscription_count"
        )

        assert podcasts[0].id == subscribed_1.id
        assert podcasts[1].id == subscribed_2.id
        assert podcasts[2].id == unsubscribed.id

        assert podcasts[0].subscription_count == 2
        assert podcasts[1].subscription_count == 1
        assert podcasts[2].subscription_count == 0


class TestPodcastModel:
    def test_slug(self):
        podcast = Podcast(title="Testing")
        assert podcast.slug == "testing"

    def test_slug_if_title_empty(self):
        assert Podcast().slug == "podcast"

    def is_subscribed_anonymous(self, podcast, anonymous_user):
        assert not podcast.is_subscribed(anonymous_user)

    def is_subscribed_false(self, podcast, user):
        assert not podcast.is_subscribed(user)

    def is_subscribed_true(self):
        sub = SubscriptionFactory()
        assert sub.podcast.is_subscribed(sub.user)

    def test_get_opengraph_data(self, rf, podcast):
        req = rf.get("/")
        og_data = podcast.get_opengraph_data(req)
        assert og_data["og:title"] == podcast.title
        assert (
            og_data["og:url"] == "http://testserver.com/" + podcast.get_absolute_url()
        )
