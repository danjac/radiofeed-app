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
    def test_for_user(self, user):

        # not recommended
        PodcastFactory()

        # subscribed
        subscribed = SubscriptionFactory(user=user).podcast

        # bookmarked
        bookmarked = BookmarkFactory(user=user).episode.podcast

        # listened
        listened = AudioLogFactory(user=user).episode.podcast

        RecommendationFactory(podcast=subscribed)
        RecommendationFactory(podcast=listened)
        RecommendationFactory(podcast=bookmarked)

        # ensure we exclude recommended
        RecommendationFactory(recommended=subscribed)
        RecommendationFactory(recommended=listened)
        RecommendationFactory(recommended=bookmarked)

        recommendations = Recommendation.objects.for_user(user)
        assert recommendations.count() == 3
        recommended = [r.recommended for r in recommendations]

        assert subscribed not in recommended
        assert listened not in recommended
        assert bookmarked not in recommended


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

    def test_with_has_subscribed_anonymous(self, anonymous_user):
        subbed_1 = PodcastFactory()
        subbed_2 = PodcastFactory()
        PodcastFactory()

        SubscriptionFactory(podcast=subbed_1)
        SubscriptionFactory(podcast=subbed_1)
        SubscriptionFactory(podcast=subbed_2)

        podcasts = Podcast.objects.with_has_subscribed(anonymous_user).filter(
            has_subscribed=True
        )
        assert podcasts.count() == 0

    def test_with_has_subscribed_authenticated(self, user):
        subbed_1 = PodcastFactory()
        subbed_2 = PodcastFactory()
        PodcastFactory()

        SubscriptionFactory(podcast=subbed_1, user=user)
        SubscriptionFactory(podcast=subbed_1)
        SubscriptionFactory(podcast=subbed_2)

        podcasts = Podcast.objects.with_has_subscribed(user).filter(has_subscribed=True)
        assert podcasts.count() == 1
        assert podcasts.first() == subbed_1

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
