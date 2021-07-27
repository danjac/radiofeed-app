from datetime import datetime

import pytest
import pytz

from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site

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

    now = datetime(2021, 7, 26, 12, 30, tzinfo=pytz.utc)

    @pytest.mark.parametrize(
        "now,last_pub,exists",
        [
            # 0: first hourly tier
            (now, datetime(2021, 7, 25, 12, 15, tzinfo=pytz.utc), True),
            # 1: second hourly tier, right hour
            (now, datetime(2021, 7, 24, 12, 15, tzinfo=pytz.utc), True),
            # 2: second hourly tier, wrong hour
            (now, datetime(2021, 7, 24, 13, 15, tzinfo=pytz.utc), False),
            # 3: third hourly tier, right hour
            (now, datetime(2021, 7, 20, 9, 15, tzinfo=pytz.utc), True),
            # 4: third hourly tier, wrong hour
            (now, datetime(2021, 7, 20, 13, 15, tzinfo=pytz.utc), False),
            # 5: first daily tier, right hour
            (now, datetime(2021, 7, 18, 12, 15, tzinfo=pytz.utc), True),
            # 6: first daily tier, wrong hour
            (now, datetime(2021, 7, 18, 13, 15, tzinfo=pytz.utc), False),
            # 7: second daily tier, right day, right hour
            (now, datetime(2021, 6, 2, 12, 15, tzinfo=pytz.utc), True),
            # 8: second daily tier, right day, wrong hour
            (now, datetime(2021, 6, 2, 13, 15, tzinfo=pytz.utc), False),
            # 9: second daily tier, wrong day, right hour
            (now, datetime(2021, 6, 1, 12, 15, tzinfo=pytz.utc), False),
            # 10: third daily tier, right day, right hour
            (now, datetime(2021, 3, 1, 12, 15, tzinfo=pytz.utc), True),
            # 11: third daily tier, right day, wrong hour
            (now, datetime(2021, 3, 1, 13, 15, tzinfo=pytz.utc), False),
            # 12: third daily tier, wrong day, right hour
            (now, datetime(2021, 3, 2, 13, 15, tzinfo=pytz.utc), False),
        ],
    )
    def test_for_feed_sync(self, db, now, last_pub, exists):
        p = PodcastFactory(active=True, pub_date=last_pub)
        print(p.pub_date)
        print([p.pub_date for p in Podcast.objects.for_feed_sync(now)])
        print(str(Podcast.objects.for_feed_sync(now).query))
        assert Podcast.objects.for_feed_sync(now).exists() is exists

    def test_for_feed_sync_no_pub_date(self, db):
        PodcastFactory(active=True, pub_date=None)
        assert not Podcast.objects.for_feed_sync().exists()

    def test_for_feed_sync_inactive(self, db):
        PodcastFactory(active=False, pub_date=None)
        assert not Podcast.objects.for_feed_sync().exists()

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
