from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.test import RequestFactory, TestCase

from audiotrails.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
)
from audiotrails.users.factories import UserFactory

from ..factories import (
    CategoryFactory,
    FollowFactory,
    PodcastFactory,
    RecommendationFactory,
)
from ..models import Category, Podcast, Recommendation


class RecommendationManagerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_bulk_delete(self):
        RecommendationFactory.create_batch(3)
        Recommendation.objects.bulk_delete()
        assert Recommendation.objects.count() == 0

    def test_for_user(self):

        following = FollowFactory(user=self.user).podcast
        favorited = FavoriteFactory(user=self.user).episode.podcast
        listened = AudioLogFactory(user=self.user).episode.podcast

        received = RecommendationFactory(
            podcast=FollowFactory(user=self.user).podcast
        ).recommended
        self.user.recommended_podcasts.add(received)

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

        recommended = [
            r.recommended for r in Recommendation.objects.for_user(self.user)
        ]

        assert len(recommended) == 3

        assert first in recommended
        assert second in recommended
        assert third in recommended


class CategoryManagerTests(TestCase):
    def test_search(self):
        CategoryFactory(name="testing")
        assert Category.objects.search("testing").count() == 1


class CategoryModelTests(TestCase):
    def test_slug(self):
        category = Category(name="Testing")
        assert category.slug == "testing"


class PodcastManagerTests(TestCase):
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


class PodcastModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.podcast = PodcastFactory()
        cls.user = UserFactory()

    def test_slug(self):
        podcast = Podcast(title="Testing")
        assert podcast.slug == "testing"

    def test_get_episode_count(self):
        EpisodeFactory.create_batch(3)
        EpisodeFactory.create_batch(3, podcast=self.podcast)
        assert self.podcast.get_episode_count() == 3

    def test_get_cached_episode_count(self):
        EpisodeFactory.create_batch(3)
        EpisodeFactory.create_batch(3, podcast=self.podcast)
        assert self.podcast.get_cached_episode_count() == 3

    def test_slug_if_title_empty(self):
        assert Podcast().slug == "podcast"

    def is_following_anonymous(self):
        assert not self.podcast.is_following(AnonymousUser())

    def is_following_false(self):
        assert not self.podcast.is_following(self.user)

    def is_following_true(self):
        sub = FollowFactory()
        assert sub.podcast.is_following(sub.user)

    def test_get_opengraph_data(self):
        req = RequestFactory().get("/")
        req.site = Site.objects.get_current()
        og_data = self.podcast.get_opengraph_data(req)
        assert self.podcast.title in og_data["title"]
        assert og_data["url"] == "http://testserver" + self.podcast.get_absolute_url()
