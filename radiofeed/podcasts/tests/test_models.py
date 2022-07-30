from __future__ import annotations

from datetime import timedelta

import pytest

from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from radiofeed.podcasts.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from radiofeed.podcasts.models import Category, Podcast, Recommendation, Subscription
from radiofeed.users.factories import UserFactory


class TestSubscriptionManager:
    def test_anonymous(self, db, anonymous_user):
        assert Subscription.objects.podcast_ids(anonymous_user) == set()

    def test_none(self, user):
        assert Subscription.objects.podcast_ids(user) == set()

    def test_subscribed(self, db):
        subscription = SubscriptionFactory()
        assert Subscription.objects.podcast_ids(subscription.subscriber) == {
            subscription.podcast_id
        }


class TestRecommendationManager:
    def test_bulk_delete(self, db):
        RecommendationFactory.create_batch(3)
        Recommendation.objects.bulk_delete()
        assert Recommendation.objects.count() == 0


class TestCategoryManager:
    @pytest.fixture
    def category(self, db):
        return CategoryFactory(name="testing", name_fi="testaaminen")

    def test_search_empty(self, category):
        assert Category.objects.search("").count() == 0

    def test_search_english(self, category):

        with override("en"):
            assert Category.objects.search("testing").count() == 1
            assert Category.objects.search("testaaminen").count() == 0

    def test_search_finnish(self, category):

        with override("fi"):
            assert Category.objects.search("testing").count() == 0
            assert Category.objects.search("testaaminen").count() == 1


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

    @pytest.mark.parametrize(
        "active,pub_date,parsed,exists",
        [
            (
                True,
                None,
                None,
                True,
            ),
            (
                False,
                None,
                None,
                False,
            ),
            (
                True,
                timedelta(hours=3),
                timedelta(hours=1),
                True,
            ),
            (
                False,
                timedelta(hours=3),
                timedelta(hours=1),
                False,
            ),
            (
                True,
                timedelta(hours=3),
                timedelta(minutes=30),
                False,
            ),
            (
                True,
                timedelta(days=3),
                timedelta(hours=3),
                True,
            ),
            (
                True,
                timedelta(days=3),
                timedelta(hours=1),
                False,
            ),
            (
                True,
                timedelta(days=8),
                timedelta(hours=8),
                True,
            ),
            (
                True,
                timedelta(days=8),
                timedelta(hours=9),
                True,
            ),
            (
                True,
                timedelta(days=14),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                timedelta(days=15),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                timedelta(days=15),
                timedelta(hours=24),
                True,
            ),
            (
                True,
                timedelta(days=24),
                timedelta(hours=24),
                True,
            ),
            (
                True,
                timedelta(days=100),
                timedelta(hours=12),
                False,
            ),
            (
                True,
                timedelta(days=100),
                timedelta(hours=100),
                True,
            ),
        ],
    )
    def test_get_scheduled_feeds(self, db, mocker, active, pub_date, parsed, exists):
        now = timezone.now()

        PodcastFactory(
            active=active,
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
        )

        assert Podcast.objects.scheduled().exists() == exists, (
            pub_date,
            parsed,
            exists,
        )


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
        assert subscription.podcast.is_subscribed(subscription.subscriber)

    def test_get_latest_episode_url(self, podcast):
        url = podcast.get_latest_episode_url()
        assert url == reverse(
            "podcasts:latest_episode", args=[podcast.id, podcast.slug]
        )

    def test_get_subscribe_target(self):
        return Podcast(id=12345).get_subscribe_target() == "subscribe-actions-12345"
