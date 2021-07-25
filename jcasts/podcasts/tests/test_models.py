import datetime

import pytest

from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.utils import timezone

from jcasts.episodes.factories import AudioLogFactory, FavoriteFactory
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

    @pytest.mark.parametrize("date", ["2021-06-19", "2021-06-18"])
    def test_for_feed_sync(self, db, freeze_time, date):
        with freeze_time(date):
            now = timezone.now()

            # no pub date yet
            podcast_a = PodcastFactory(pub_date=None)

            # 3 days ago: first tier
            podcast_b = PodcastFactory(pub_date=now - datetime.timedelta(days=3))

            # 100 days ago: even/odd day
            podcast_c = PodcastFactory(pub_date=now - datetime.timedelta(days=100))

            # 203 days ago: matching weekday
            podcast_d = PodcastFactory(pub_date=now - datetime.timedelta(days=203))

            # last checked > 4 hours ago
            podcast_e = PodcastFactory(
                pub_date=None, last_checked=now - datetime.timedelta(hours=6)
            )

            # not included:

            # last checked < 1 hour ago
            PodcastFactory(
                pub_date=None, last_checked=now - datetime.timedelta(hours=1)
            )

            # 200 days ago: Tuesday
            PodcastFactory(pub_date=now - datetime.timedelta(days=200))

            # 99 days ago: odd day
            PodcastFactory(pub_date=now - datetime.timedelta(days=99))

            # inactive: never include
            PodcastFactory(active=False)

            # just updated
            PodcastFactory(pub_date=now - datetime.timedelta(hours=1))

            qs = Podcast.objects.for_feed_sync()
            assert qs.count() == 5
            assert podcast_a in qs
            assert podcast_b in qs
            assert podcast_c in qs
            assert podcast_d in qs
            assert podcast_e in qs

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
