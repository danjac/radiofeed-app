from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.utils import timezone

from jcasts.episodes.factories import AudioLogFactory, EpisodeFactory, FavoriteFactory
from jcasts.podcasts.factories import (
    CategoryFactory,
    FollowFactory,
    PodcastFactory,
    RecommendationFactory,
)
from jcasts.podcasts.models import Category, Podcast, Recommendation
from jcasts.users.factories import UserFactory


class TestRecommendationManager:
    def test_bulk_delete(self, db):
        RecommendationFactory.create_batch(3)
        Recommendation.objects.bulk_delete()
        assert Recommendation.objects.count() == 0

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
    def test_search(self, db):
        CategoryFactory(name="testing")
        assert Category.objects.search("testing").count() == 1


class TestCategoryModel:
    def test_slug(self):
        category = Category(name="Testing")
        assert category.slug == "testing"

    def test_str(self):
        category = Category(name="Testing")
        assert str(category) == "Testing"


class TestPodcastManager:
    reltuple_count = "jcasts.shared.db.get_reltuple_count"

    def test_search(self, db):
        PodcastFactory(title="testing")
        assert Podcast.objects.search("testing").count() == 1

    def test_search_if_empty(self, db):
        PodcastFactory(title="testing")
        assert Podcast.objects.search("").count() == 0

    def test_count_if_gt_1000(self, db, mocker):
        mocker.patch(self.reltuple_count, return_value=2000)
        assert Podcast.objects.count() == 2000

    def test_count_if_lt_1000(self, db, mocker, podcast):
        mocker.patch(self.reltuple_count, return_value=100)
        assert Podcast.objects.count() == 1

    def test_count_if_filter(self, db, mocker):
        mocker.patch(self.reltuple_count, return_value=2000)
        PodcastFactory(title="test")
        assert Podcast.objects.filter(title="test").count() == 1


class TestPodcastModel:
    def test_slug(self):
        assert Podcast(title="Testing").slug == "testing"

    def test_slug_if_title_empty(self):
        assert Podcast().slug == "podcast"

    def test_get_domain(self):
        assert Podcast(rss="https://example.com/rss.xml").get_domain() == "example.com"

    def test_get_domain_if_www(self):
        assert (
            Podcast(rss="https://www.example.com/rss.xml").get_domain() == "example.com"
        )

    def test_cleaned_title(self):
        podcast = Podcast(title="<b>a &amp; b</b>")
        assert podcast.cleaned_title == "a & b"

    def test_is_following_anonymous(self, podcast):
        assert not podcast.is_following(AnonymousUser())

    def test_is_following_false(self, podcast):
        assert not podcast.is_following(UserFactory())

    def test_is_following_true(self, follow):
        assert follow.podcast.is_following(follow.user)

    def test_get_opengraph_data(self, rf, podcast):
        req = rf.get("/")
        req.site = Site.objects.get_current()
        og_data = podcast.get_opengraph_data(req)
        assert podcast.title in og_data["title"]
        assert og_data["url"] == "http://testserver" + podcast.get_absolute_url()

    def test_get_next_scheduled_feed_update_inactive(self):
        assert (
            Podcast(
                pub_date=timezone.now(), active=False
            ).get_next_scheduled_feed_update()
            is None
        )

    def test_get_next_scheduled_feed_update_no_pub_date(self):
        assert (
            Podcast(pub_date=None, active=True).get_next_scheduled_feed_update() is None
        )

    def test_get_next_scheduled_feed_update_no_episodes(self, podcast):
        # should be no more than a day if no episodes found
        scheduled = podcast.get_next_scheduled_feed_update()
        assert (scheduled - timezone.now()).days < 1

    def test_get_next_scheduled_feed_update_three_days(self, podcast):

        # approx 1 a week between episodes
        now = timezone.now().replace(hour=0, minute=0)

        EpisodeFactory(
            podcast=podcast, pub_date=(now - timedelta(days=2)).replace(hour=12)
        )

        EpisodeFactory(
            podcast=podcast, pub_date=(now - timedelta(days=5)).replace(hour=18)
        )

        EpisodeFactory(
            podcast=podcast, pub_date=(now - timedelta(days=8)).replace(hour=9)
        )

        scheduled = podcast.get_next_scheduled_feed_update()
        assert scheduled.hour == 12
        # every three days, so should run tomorrow
        assert (scheduled - timezone.now()).days == 1

    def test_get_next_scheduled_feed_update_one_week(self, podcast):

        # approx 1 a week between episodes
        now = timezone.now().replace(hour=0, minute=0)

        EpisodeFactory(
            podcast=podcast, pub_date=(now - timedelta(days=7)).replace(hour=12)
        )

        EpisodeFactory(
            podcast=podcast, pub_date=(now - timedelta(days=14)).replace(hour=18)
        )

        EpisodeFactory(
            podcast=podcast, pub_date=(now - timedelta(days=21)).replace(hour=9)
        )

        scheduled = podcast.get_next_scheduled_feed_update()
        assert scheduled.hour == 12
        # should be today, as last time 7 days ago
        assert (scheduled - timezone.now()).days == 0

    def test_get_next_scheduled_feed_update_last_episode_month_diff(self, podcast):

        # approx one month between episodes, but last episode yesterday. Should be max
        # 1 week
        now = timezone.now().replace(hour=12, minute=0)

        EpisodeFactory(podcast=podcast, pub_date=now - timedelta(days=1))
        EpisodeFactory(podcast=podcast, pub_date=now - timedelta(days=31))
        EpisodeFactory(podcast=podcast, pub_date=now - timedelta(days=61))

        scheduled = podcast.get_next_scheduled_feed_update()
        assert (scheduled - timezone.now()).days in (7, 8)

    def test_get_next_scheduled_feed_update_last_episode_month_ago(self, podcast):

        # approx 1 a week between episodes, but last episode thirty days ago
        now = timezone.now().replace(hour=12, minute=0)

        EpisodeFactory(podcast=podcast, pub_date=now - timedelta(days=30))
        EpisodeFactory(podcast=podcast, pub_date=now - timedelta(days=37))
        EpisodeFactory(podcast=podcast, pub_date=now - timedelta(days=44))

        scheduled = podcast.get_next_scheduled_feed_update()
        assert (scheduled - timezone.now()).days == 7
