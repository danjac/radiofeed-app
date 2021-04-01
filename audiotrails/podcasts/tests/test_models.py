# Third Party Libraries
import pytest

# RadioFeed
from audiotrails.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
)

# Local
from ..factories import (
    CategoryFactory,
    FollowFactory,
    PodcastFactory,
    RecommendationFactory,
)
from ..models import Category, Podcast, Recommendation

pytestmark = pytest.mark.django_db


class TestRecommendationManager:
    def test_for_user(self, user):

        following = FollowFactory(user=user).podcast
        favorited = FavoriteFactory(user=user).episode.podcast
        listened = AudioLogFactory(user=user).episode.podcast

        received = RecommendationFactory(
            podcast=FollowFactory(user=user).podcast
        ).recommended
        user.recommended_podcasts.add(received)

        first = RecommendationFactory(podcast=following).recommended
        second = RecommendationFactory(podcast=favorited).recommended
        third = RecommendationFactory(podcast=listened).recommended

        # already received

        # not connected
        RecommendationFactory()

        # already following, listened to or favorited
        RecommendationFactory(recommended=following)
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

    def test_with_follow_count(self):
        following_1 = PodcastFactory()
        following_2 = PodcastFactory()
        not_following = PodcastFactory()

        FollowFactory(podcast=following_1)
        FollowFactory(podcast=following_1)
        FollowFactory(podcast=following_2)

        podcasts = Podcast.objects.with_follow_count().order_by("-follow_count")

        assert podcasts[0].id == following_1.id
        assert podcasts[1].id == following_2.id
        assert podcasts[2].id == not_following.id

        assert podcasts[0].follow_count == 2
        assert podcasts[1].follow_count == 1
        assert podcasts[2].follow_count == 0


class TestPodcastModel:
    def test_slug(self):
        podcast = Podcast(title="Testing")
        assert podcast.slug == "testing"

    def test_get_cached_episode_count(self, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        assert podcast.get_cached_episode_count() == 3

    def test_slug_if_title_empty(self):
        assert Podcast().slug == "podcast"

    def is_following_anonymous(self, podcast, anonymous_user):
        assert not podcast.is_following(anonymous_user)

    def is_following_false(self, podcast, user):
        assert not podcast.is_following(user)

    def is_following_true(self):
        sub = FollowFactory()
        assert sub.podcast.is_following(sub.user)

    def test_get_opengraph_data(self, rf, podcast, site):
        req = rf.get("/")
        req.site = site
        og_data = podcast.get_opengraph_data(req)
        assert podcast.title in og_data["title"]
        assert og_data["url"] == "http://testserver" + podcast.get_absolute_url()
