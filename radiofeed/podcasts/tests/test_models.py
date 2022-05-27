from datetime import timedelta

import pytest

from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.utils import timezone

from radiofeed.episodes.factories import AudioLogFactory, BookmarkFactory
from radiofeed.podcasts.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from radiofeed.podcasts.models import Category, Podcast, Recommendation
from radiofeed.users.factories import UserFactory


class TestRecommendationManager:
    def test_bulk_delete(self, db):
        RecommendationFactory.create_batch(3)
        Recommendation.objects.bulk_delete()
        assert Recommendation.objects.count() == 0

    def test_for_user(self, user):

        following = SubscriptionFactory(user=user).podcast
        favorited = BookmarkFactory(user=user).episode.podcast
        listened = AudioLogFactory(user=user).episode.podcast

        received = RecommendationFactory(
            podcast=SubscriptionFactory(user=user).podcast
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
    reltuple_count = "radiofeed.common.db.get_reltuple_count"

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

    def test_with_subscribed_true(self, db):
        SubscriptionFactory()
        assert Podcast.objects.with_subscribed().first().subscribed

    def test_with_subscribed_false(self, db):
        PodcastFactory()
        assert not Podcast.objects.with_subscribed().first().subscribed

    def test_scheduled_not_parsed(self, db):
        PodcastFactory(parsed=None)
        assert Podcast.objects.scheduled().exists()

    @pytest.mark.parametrize(
        "parsed,pub_date,exists",
        [
            (timedelta(minutes=30), timedelta(days=7), False),
            (timedelta(hours=2), timedelta(hours=6), True),
            (timedelta(hours=3), timedelta(days=7), True),
            (timedelta(hours=2), timedelta(days=7), True),
            (timedelta(hours=3), timedelta(days=15), True),
            (timedelta(hours=9), timedelta(days=15), True),
        ],
    )
    def test_scheduled_subscribed(self, db, parsed, pub_date, exists):
        now = timezone.now()
        SubscriptionFactory(
            podcast__parsed=now - parsed,
            podcast__pub_date=now - pub_date,
        )
        assert Podcast.objects.scheduled().exists() == exists

    @pytest.mark.parametrize(
        "parsed,pub_date,exists",
        [
            (timedelta(minutes=30), timedelta(days=7), False),
            (timedelta(hours=2), timedelta(hours=6), True),
            (timedelta(hours=3), timedelta(days=7), True),
            (timedelta(hours=2), timedelta(days=7), True),
            (timedelta(hours=3), timedelta(days=15), True),
            (timedelta(hours=9), timedelta(days=15), True),
        ],
    )
    def test_scheduled_promoted(self, db, parsed, pub_date, exists):
        now = timezone.now()
        PodcastFactory(
            promoted=True,
            parsed=now - parsed,
            pub_date=now - pub_date,
        )
        assert Podcast.objects.scheduled().exists() == exists

    @pytest.mark.parametrize(
        "parsed,pub_date,exists",
        [
            (timedelta(hours=2), timedelta(hours=6), False),
            (timedelta(hours=3), timedelta(days=7), True),
            (timedelta(hours=2), timedelta(days=7), False),
            (timedelta(minutes=30), timedelta(days=7), False),
            (timedelta(hours=3), timedelta(days=15), False),
            (timedelta(hours=9), timedelta(days=15), True),
        ],
    )
    def test_scheduled(self, db, parsed, pub_date, exists):
        now = timezone.now()
        PodcastFactory(
            parsed=now - parsed,
            pub_date=now - pub_date,
        )
        assert Podcast.objects.scheduled().exists() == exists


class TestPodcastModel:
    def test_str(self):
        assert str(Podcast(title="title")) == "title"

    def test_str_title_empty(self):
        rss = "https://example.com/rss.xml"
        assert str(Podcast(title="", rss=rss)) == rss

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

    def test_is_subscribed_anonymous(self, podcast):
        assert not podcast.is_subscribed(AnonymousUser())

    def test_is_subscribed_false(self, podcast):
        assert not podcast.is_subscribed(UserFactory())

    def test_is_subscribed_true(self, subscription):
        assert subscription.podcast.is_subscribed(subscription.user)

    def test_get_latest_episode_url(self, podcast):
        url = podcast.get_latest_episode_url()
        assert url == reverse(
            "podcasts:latest_episode", args=[podcast.id, podcast.slug]
        )

    def test_get_subscribe_target(self):
        return Podcast(id=12345).get_subscribe_target() == "subscribe-buttons-12345"
