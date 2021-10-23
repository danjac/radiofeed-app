from datetime import timedelta

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
    hub = "https://pubsubhubbub.appspot.com/"

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

    def test_exact_match(self, db):
        exact = PodcastFactory(title="testing")
        PodcastFactory(title="test")
        PodcastFactory(title="nomatch")

        podcasts = Podcast.objects.with_exact_match("testing").order_by("-exact_match")
        assert podcasts.count() == 3
        first = podcasts.first()
        assert first == exact
        assert first.exact_match

        second = podcasts[1]
        assert not second.exact_match

        third = podcasts[2]
        assert not third.exact_match

    def test_search_or_exact_match(self, db):
        exact = PodcastFactory(title="test")
        inexact = PodcastFactory(title="test a thing")
        PodcastFactory(title="nomatch")

        podcasts = Podcast.objects.search_or_exact_match("test").order_by(
            "-exact_match",
            "-rank",
        )
        assert podcasts.count() == 2
        first = podcasts.first()
        assert first == exact
        assert first.exact_match

        second = podcasts[1]
        assert second == inexact
        assert not second.exact_match

    def test_inactive(self, db):
        PodcastFactory(active=False)
        assert Podcast.objects.active().count() == 0

    def test_active(self, db):
        PodcastFactory(active=True)
        assert Podcast.objects.active().count() == 1

    def test_published_pub_date_not_null(self, db):
        PodcastFactory(pub_date=timezone.now())
        assert Podcast.objects.published().count() == 1

    def test_published_pub_date_null(self, db):
        PodcastFactory(pub_date=None)
        assert Podcast.objects.published().count() == 0

    def test_unpublished_pub_date_not_null(self, db):
        PodcastFactory(pub_date=timezone.now())
        assert Podcast.objects.unpublished().count() == 0

    def test_unpublished_pub_date_null(self, db):
        PodcastFactory(pub_date=None)
        assert Podcast.objects.unpublished().count() == 1

    def test_with_followed_true(self, db):
        FollowFactory()
        assert Podcast.objects.with_followed().first().followed

    def test_with_followed_false(self, db):
        PodcastFactory()
        assert not Podcast.objects.with_followed().first().followed

    @pytest.mark.parametrize(
        "polled,queued,exists",
        [
            (None, False, True),
            (timedelta(days=-3), False, True),
            (timedelta(days=3), False, False),
            (None, True, False),
            (timedelta(days=-3), True, False),
            (timedelta(days=3), True, False),
        ],
    )
    def test_scheduled(self, db, polled, queued, exists):

        now = timezone.now()
        PodcastFactory(
            polled=now + polled if polled else None,
            queued=now if queued else None,
        )
        assert Podcast.objects.scheduled(timedelta(hours=1)).exists() is exists

    @pytest.mark.parametrize(
        "last_pub,exists",
        [
            (timedelta(days=30), True),
            (timedelta(days=99), False),
            (None, True),
        ],
    )
    def test_fresh(self, db, settings, last_pub, exists):
        settings.FRESHNESS_THRESHOLD = timedelta(days=90)
        PodcastFactory(pub_date=timezone.now() - last_pub if last_pub else None)

        assert Podcast.objects.fresh().exists() is exists

    @pytest.mark.parametrize(
        "last_pub,exists",
        [
            (timedelta(days=30), False),
            (timedelta(days=99), True),
            (None, False),
        ],
    )
    def test_stale(self, db, settings, last_pub, exists):
        settings.FRESHNESS_THRESHOLD = timedelta(days=90)
        PodcastFactory(pub_date=timezone.now() - last_pub if last_pub else None)

        assert Podcast.objects.stale().exists() is exists


class TestPodcastModel:
    rss = "https://example.com/rss.xml"

    def test_str(self):
        assert str(Podcast(title="title")) == "title"

    def test_str_title_empty(self):
        assert str(Podcast(title="", rss=self.rss)) == self.rss

    def test_slug(self):
        assert Podcast(title="Testing").slug == "testing"

    def test_slug_if_title_empty(self):
        assert Podcast().slug == "no-title"

    def test_cleaned_title(self):
        podcast = Podcast(title="<b>Test &amp; Code")
        assert podcast.cleaned_title == "Test & Code"

    def test_cleaned_description(self):
        podcast = Podcast(description="<b>Test &amp; Code")
        assert podcast.cleaned_description == "Test & Code"

    def test_get_domain(self):
        assert Podcast(rss=self.rss).get_domain() == "example.com"

    def test_get_domain_if_www(self):
        assert Podcast(rss=self.rss).get_domain() == "example.com"

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
