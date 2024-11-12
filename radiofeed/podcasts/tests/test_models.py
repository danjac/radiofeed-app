from datetime import timedelta

import pytest
from django.utils import timezone

from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.podcasts.models import Category, Podcast, Recommendation, Subscription
from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)


class TestRecommendationManager:
    @pytest.mark.django_db
    def test_bulk_delete(self):
        RecommendationFactory.create_batch(3)
        Recommendation.objects.bulk_delete()
        assert Recommendation.objects.count() == 0

    @pytest.mark.django_db
    def test_with_relevance(self):
        RecommendationFactory(similarity=0.5, frequency=3)
        recommendation = Recommendation.objects.with_relevance().first()
        assert recommendation.relevance == 1.5


class TestRecommendationModel:
    def test_str(self):
        assert (
            str(Recommendation(podcast_id=1, recommended_id=2))
            == "podcast 1 | recommended 2"
        )


class TestCategoryManager:
    @pytest.fixture
    def category(self):
        return CategoryFactory(name="testing")

    @pytest.mark.django_db
    def test_search_empty(self, category):
        assert Category.objects.search("").count() == 0

    @pytest.mark.django_db
    def test_search(self, category):
        assert Category.objects.search("testing").count() == 1


class TestCategoryModel:
    def test_slug(self):
        category = Category(name="Testing")
        assert category.slug == "testing"

    def test_str(self):
        category = Category(name="Testing")
        assert str(category) == "Testing"


class TestPodcastManager:
    @pytest.mark.django_db
    def test_search(self):
        PodcastFactory(title="testing")
        assert Podcast.objects.search("testing").count() == 1

    @pytest.mark.django_db
    def test_search_no_results(self):
        PodcastFactory(title="testing")
        assert Podcast.objects.search("random").count() == 0

    @pytest.mark.django_db
    def test_search_partial(self):
        PodcastFactory(title="testing")
        assert Podcast.objects.search("test").count() == 1

    @pytest.mark.django_db
    def test_search_owner(self):
        PodcastFactory(owner="tester")
        assert Podcast.objects.search("tester").count() == 1

    @pytest.mark.django_db
    def test_search_keywords(self):
        PodcastFactory(keywords="test")
        assert Podcast.objects.search("test").count() == 1

    @pytest.mark.django_db
    def test_search_if_empty(self):
        PodcastFactory(title="testing")
        assert Podcast.objects.search("").count() == 0

    @pytest.mark.django_db
    def test_search_title_fallback(self):
        # usually "the" would be removed by stemmer
        PodcastFactory(title="the")
        podcasts = Podcast.objects.search("the")
        assert podcasts.count() == 1
        assert podcasts.first().exact_match == 1

    @pytest.mark.django_db
    def test_compare_exact_and_partial_matches_in_search(self):
        PodcastFactory(title="the testing")
        PodcastFactory(title="testing")

        podcasts = Podcast.objects.search("testing").order_by("-exact_match")

        assert podcasts.count() == 2

        first = podcasts[0]
        second = podcasts[1]

        assert first.title == "testing"
        assert first.exact_match == 1

        assert second.title == "the testing"
        assert second.exact_match == 0

    @pytest.mark.django_db
    def test_subscribed_true(self, user):
        SubscriptionFactory(subscriber=user)
        assert Podcast.objects.subscribed(user).exists() is True

    @pytest.mark.django_db
    def test_subscribed_false(self, user, podcast):
        assert Podcast.objects.subscribed(user).exists() is False

    @pytest.mark.parametrize(
        ("published", "arg", "result"),
        [
            pytest.param(True, True, True, id="pub_date NOT NULL, arg is True"),
            pytest.param(True, False, False, id="pub_date NOT NULL, arg is False"),
            pytest.param(False, True, False, id="pub_date NULL, arg is True"),
            pytest.param(False, False, True, id="pub_date NULL, arg is False"),
        ],
    )
    @pytest.mark.django_db
    def test_published_true(self, published, arg, result):
        PodcastFactory(pub_date=timezone.now() if published else None)
        assert Podcast.objects.published(published=arg).exists() is result

    @pytest.mark.parametrize(
        ("kwargs", "exists"),
        [
            pytest.param(
                {},
                True,
                id="parsed is None",
            ),
            pytest.param(
                {"frequency": timedelta(hours=3)},
                True,
                id="parsed is None",
            ),
            pytest.param(
                {
                    "parsed": timedelta(hours=3),
                    "frequency": timedelta(hours=1),
                },
                True,
                id="pub date is None",
            ),
            pytest.param(
                {
                    "parsed": timedelta(seconds=1200),
                    "pub_date": timedelta(days=3),
                    "frequency": timedelta(hours=3),
                },
                False,
                id="just parsed",
            ),
            pytest.param(
                {
                    "parsed": timedelta(hours=3),
                    "pub_date": timedelta(days=3),
                    "frequency": timedelta(hours=3),
                },
                True,
                id="parsed before pub date+frequency",
            ),
            pytest.param(
                {
                    "parsed": timedelta(days=8),
                    "pub_date": timedelta(days=8),
                    "frequency": timedelta(days=15),
                },
                True,
                id="parsed just before max frequency",
            ),
            pytest.param(
                {
                    "parsed": timedelta(days=30),
                    "pub_date": timedelta(days=90),
                    "frequency": timedelta(days=30),
                },
                True,
                id="parsed before max frequency",
            ),
        ],
    )
    @pytest.mark.django_db
    def test_get_scheduled_podcasts(self, kwargs, exists):
        now = timezone.now()

        parsed = kwargs.get("parsed", None)
        pub_date = kwargs.get("pub_date", None)

        frequency = kwargs.get("frequency", Podcast.DEFAULT_PARSER_FREQUENCY)

        PodcastFactory(
            frequency=frequency,
            parsed=now - parsed if parsed else None,
            pub_date=now - pub_date if pub_date else None,
        )

        assert Podcast.objects.scheduled().exists() is exists

    @pytest.mark.django_db
    def test_recommended(self, user):
        podcast = SubscriptionFactory(subscriber=user).podcast
        RecommendationFactory.create_batch(3, podcast=podcast)
        PodcastFactory(promoted=True)
        assert Podcast.objects.recommended(user).count() == 4

    @pytest.mark.django_db
    def test_recommended_is_subscribed(self, user):
        podcast = SubscriptionFactory(subscriber=user).podcast
        RecommendationFactory(recommended=podcast)
        assert Podcast.objects.recommended(user).count() == 0


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

    @pytest.mark.django_db
    def test_has_similar_none(self, podcast):
        assert podcast.has_similar is False

    @pytest.mark.django_db
    def test_has_similar_has_recommendations(self, podcast):
        RecommendationFactory.create_batch(3, podcast=podcast)
        assert podcast.has_similar is True

    @pytest.mark.django_db
    def test_has_similar_is_private(self):
        assert Podcast(private=True).has_similar is False

    @pytest.mark.django_db
    def test_num_episodes_none(self, podcast):
        assert podcast.num_episodes == 0

    @pytest.mark.django_db
    def test_num_episodes(self, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        assert podcast.num_episodes == 3

    def test_get_next_scheduled_update_pub_date_none(self):
        now = timezone.now()
        podcast = Podcast(
            parsed=now - timedelta(hours=1), pub_date=None, frequency=timedelta(hours=3)
        )
        self.assert_hours_diff(podcast.get_next_scheduled_update() - now, 2)

    def test_get_next_scheduled_update_frequency_none(self):
        now = timezone.now()
        podcast = Podcast(
            parsed=now - timedelta(hours=1), pub_date=None, frequency=None
        )
        assert (podcast.get_next_scheduled_update() - now).total_seconds() < 10

    def test_get_next_scheduled_update_parsed_none(self):
        now = timezone.now()
        podcast = Podcast(
            pub_date=now - timedelta(hours=3), parsed=None, frequency=timedelta(hours=3)
        )
        assert (podcast.get_next_scheduled_update() - now).total_seconds() < 10

    def test_get_next_scheduled_update_parsed_gt_max(self):
        now = timezone.now()
        podcast = Podcast(
            pub_date=now,
            parsed=now,
            frequency=timedelta(days=30),
        )
        self.assert_hours_diff(podcast.get_next_scheduled_update() - now, 72)

    def test_get_next_scheduled_update_parsed_lt_now(self):
        now = timezone.now()
        podcast = Podcast(
            pub_date=now - timedelta(days=5),
            parsed=now - timedelta(days=16),
            frequency=timedelta(days=30),
        )
        assert (podcast.get_next_scheduled_update() - now).total_seconds() < 10

    def test_get_next_scheduled_update_pub_date_lt_now(self):
        now = timezone.now()
        podcast = Podcast(
            pub_date=now - timedelta(days=33),
            parsed=now - timedelta(days=3),
            frequency=timedelta(days=30),
        )
        assert (podcast.get_next_scheduled_update() - now).total_seconds() < 10

    def test_get_next_scheduled_update_pub_date_in_future(self):
        now = timezone.now()
        podcast = Podcast(
            pub_date=now - timedelta(days=1),
            parsed=now - timedelta(hours=1),
            frequency=timedelta(days=7),
        )
        self.assert_hours_diff(podcast.get_next_scheduled_update() - now, 71)

    def test_get_next_scheduled_update_pub_date_lt_min(self):
        now = timezone.now()
        podcast = Podcast(
            pub_date=now - timedelta(hours=3),
            parsed=now - timedelta(minutes=30),
            frequency=timedelta(hours=3),
        )

        self.assert_hours_diff(podcast.get_next_scheduled_update() - now, 0.5)

    def assert_hours_diff(self, delta, hours):
        assert delta.total_seconds() / 3600 == pytest.approx(hours)


class TestSubscriptionModel:
    def test_str(self):
        assert (
            str(Subscription(podcast_id=1, subscriber_id=2))
            == "subscriber 2 | podcast 1"
        )
