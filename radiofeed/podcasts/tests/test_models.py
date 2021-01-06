# Third Party Libraries
import pytest

# RadioFeed
from radiofeed.episodes.factories import AudioLogFactory, BookmarkFactory

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
    def test_with_subscribed_anonymous(self, anonymous_user):
        subscribed_1 = PodcastFactory()
        subscribed_2 = PodcastFactory()
        PodcastFactory()

        SubscriptionFactory(podcast=subscribed_1)
        SubscriptionFactory(podcast=subscribed_1)
        SubscriptionFactory(podcast=subscribed_2)

        RecommendationFactory(recommended=subscribed_1)

        recommendations = Podcast.objects.with_subscribed(anonymous_user).filter(
            is_subscribed=True
        )
        assert recommendations.count() == 0

    def test_with_subscribed_authenticated(self, user):
        subscribed_1 = PodcastFactory()
        subscribed_2 = PodcastFactory()
        PodcastFactory()

        SubscriptionFactory(podcast=subscribed_1, user=user)
        SubscriptionFactory(podcast=subscribed_1)
        SubscriptionFactory(podcast=subscribed_2)

        RecommendationFactory(recommended=subscribed_1)

        recommendations = (
            Recommendation.objects.with_subscribed(user)
            .filter(is_subscribed=True)
            .select_related("recommended")
        )
        assert recommendations.count() == 1
        assert recommendations.first().recommended == subscribed_1

    def test_for_user(self, user):

        subscribed = SubscriptionFactory(user=user).podcast
        bookmarked = BookmarkFactory(user=user).episode.podcast
        listened = AudioLogFactory(user=user).episode.podcast

        received = RecommendationFactory(
            podcast=SubscriptionFactory(user=user).podcast
        ).recommended
        user.recommended_podcasts.add(received)

        first = RecommendationFactory(podcast=subscribed).recommended
        second = RecommendationFactory(podcast=bookmarked).recommended
        third = RecommendationFactory(podcast=listened).recommended

        # already received

        # not connected
        RecommendationFactory()

        # already subscribed, listened to or bookmarked
        RecommendationFactory(recommended=subscribed)
        RecommendationFactory(recommended=bookmarked)
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

    def test_with_subscribed_anonymous(self, anonymous_user):
        subscribed_1 = PodcastFactory()
        subscribed_2 = PodcastFactory()
        PodcastFactory()

        SubscriptionFactory(podcast=subscribed_1)
        SubscriptionFactory(podcast=subscribed_1)
        SubscriptionFactory(podcast=subscribed_2)

        podcasts = Podcast.objects.with_subscribed(anonymous_user).filter(
            is_subscribed=True
        )
        assert podcasts.count() == 0

    def test_with_subscribed_authenticated(self, user):
        subscribed_1 = PodcastFactory()
        subscribed_2 = PodcastFactory()
        PodcastFactory()

        SubscriptionFactory(podcast=subscribed_1, user=user)
        SubscriptionFactory(podcast=subscribed_1)
        SubscriptionFactory(podcast=subscribed_2)

        podcasts = Podcast.objects.with_subscribed(user).filter(is_subscribed=True)
        assert podcasts.count() == 1
        assert podcasts.first() == subscribed_1

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
