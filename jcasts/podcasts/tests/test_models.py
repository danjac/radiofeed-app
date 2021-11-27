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

    def test_enqueue(self, db):
        podcast = PodcastFactory(queued=None)
        Podcast.objects.enqueue()
        podcast.refresh_from_db()
        assert podcast.queued

    def test_queued_true(self, db):
        PodcastFactory(queued=timezone.now())
        assert Podcast.objects.queued().exists()

    def test_queued_false(self, db):
        PodcastFactory(queued=None)
        assert not Podcast.objects.queued().exists()

    def test_unqueued_false(self, db):
        PodcastFactory(queued=timezone.now())
        assert not Podcast.objects.unqueued().exists()

    def test_unqueued_true(self, db):
        PodcastFactory(queued=None)
        assert Podcast.objects.unqueued().exists()

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
        assert Podcast.objects.inactive().count() == 1

    def test_active(self, db):
        PodcastFactory(active=True)
        assert Podcast.objects.active().count() == 1
        assert Podcast.objects.inactive().count() == 0

    def test_active_too_many_failures(self, db):
        PodcastFactory(active=True, num_failures=4)
        assert Podcast.objects.active().count() == 0
        assert Podcast.objects.inactive().count() == 1

    def test_active_failures_under_limit(self, db):
        PodcastFactory(active=True, num_failures=2)
        assert Podcast.objects.active().count() == 1
        assert Podcast.objects.inactive().count() == 0

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
        "pub_date,parsed,frequency,exists",
        [
            (None, None, None, True),
            (timedelta(days=3), None, None, True),
            (timedelta(days=3), None, timedelta(days=1), True),
            (timedelta(days=3), timedelta(days=1), timedelta(days=1), True),
            (timedelta(days=3), timedelta(days=1), timedelta(days=7), False),
            (timedelta(days=3), timedelta(days=1), timedelta(days=4), False),
            (timedelta(days=-3), timedelta(days=1), timedelta(days=1), False),
            (timedelta(days=33), None, timedelta(days=30), True),
            (timedelta(days=33), timedelta(days=1), timedelta(days=30), False),
            (timedelta(days=33), timedelta(days=30), timedelta(days=30), True),
        ],
    )
    def test_scheduled(self, db, pub_date, parsed, frequency, exists):

        now = timezone.now()

        PodcastFactory(
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
            frequency=frequency,
        )
        assert Podcast.objects.scheduled().exists() is exists, (
            pub_date,
            parsed,
            frequency,
        )

    @pytest.mark.parametrize(
        "last_pub,exists",
        [
            (timedelta(days=30), True),
            (timedelta(days=99), False),
            (None, True),
        ],
    )
    def test_relevant(self, db, last_pub, exists):
        PodcastFactory(pub_date=timezone.now() - last_pub if last_pub else None)

        assert Podcast.objects.relevant().exists() is exists


class TestPodcastModel:
    rss = "https://example.com/rss.xml"

    def test_str(self):
        assert str(Podcast(title="title")) == "title"

    def test_str_title_empty(self):
        assert str(Podcast(title="", rss=self.rss)) == self.rss

    @pytest.mark.parametrize(
        "frequency,pub_date,parsed,days",
        [
            (None, None, None, None),
            (timedelta(days=1), None, None, None),
            (timedelta(days=30), None, None, None),
            (timedelta(days=7), timedelta(days=3), None, None),
            (timedelta(days=7), timedelta(days=3), timedelta(days=1), 4),
            (timedelta(days=30), timedelta(days=9), timedelta(days=3), 27),
            (timedelta(days=30), timedelta(days=9), timedelta(days=33), None),
        ],
    )
    def test_get_scheduled(self, frequency, pub_date, parsed, days):
        now = timezone.now()
        podcast = Podcast(
            frequency=frequency,
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
        )
        scheduled = podcast.get_scheduled()
        if days is None:
            assert scheduled is None, (frequency, pub_date, parsed)
        else:
            assert (scheduled - now).days == days, (frequency, pub_date, parsed)

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
