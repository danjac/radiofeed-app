import pytest

from radiofeed.podcasts.models import Category, Recommendation
from radiofeed.podcasts.recommender import get_categories, recommend
from radiofeed.podcasts.tests.factories import (
    PodcastFactory,
    RecommendationFactory,
)


class TestRecommender:
    @pytest.mark.django_db
    def test_no_suitable_matches_for_podcasts(self):
        PodcastFactory(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )

        recommend("en")

        assert Recommendation.objects.count() == 0


class TestRecommend:
    @pytest.fixture(autouse=True)
    def clear_categories(self):
        get_categories.cache_clear()

    @pytest.mark.django_db
    def test_handle_empty_data_frame(self):
        PodcastFactory(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )

        recommend("en")
        assert Recommendation.objects.count() == 0

    @pytest.mark.django_db
    def test_no_categories(self):
        podcast_1 = PodcastFactory(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )
        PodcastFactory(
            title="Another cool science podcast",
            keywords="science physics astronomy",
        )
        PodcastFactory(title="Philosophy things", keywords="thinking")
        recommend("en")
        recommendations = (
            Recommendation.objects.filter(podcast=podcast_1)
            .order_by("similarity")
            .select_related("recommended")
        )
        assert recommendations.count() == 0

    @pytest.mark.django_db
    def test_create_recommendations(self):
        Category.objects.bulk_create(
            [
                Category(name=name)
                for name in (
                    "Science",
                    "Philosophy",
                    "Society & Culture",
                )
            ],
            ignore_conflicts=True,
        )
        cat_1 = Category.objects.get(name="Science")
        cat_2 = Category.objects.get(name="Philosophy")
        cat_3 = Category.objects.get(name="Society & Culture")
        podcast_1 = PodcastFactory(
            extracted_text="Cool science podcast science physics astronomy",
            categories=[cat_1],
            title="podcast 1",
        )
        podcast_2 = PodcastFactory(
            extracted_text="Another cool science podcast science physics astronomy",
            categories=[cat_1, cat_2],
            title="podcast 2",
        )

        # ensure old recommendations are removed
        RecommendationFactory(
            podcast=podcast_1, recommended=PodcastFactory(title="podcast 4")
        )
        RecommendationFactory(
            podcast=podcast_2, recommended=PodcastFactory(title="podcast 5")
        )

        # must have at least one category in common
        PodcastFactory(
            extracted_text="Philosophy things thinking",
            title="podcast 3",
            categories=[cat_2, cat_3],
        )

        recommend("en")

        recommendations = (
            Recommendation.objects.filter(podcast=podcast_1)
            .order_by("similarity")
            .select_related("recommended")
        )
        assert recommendations.count() == 1

        assert recommendations[0].recommended == podcast_2

        recommendations = (
            Recommendation.objects.filter(podcast=podcast_2)
            .order_by("similarity")
            .select_related("recommended")
        )
        assert recommendations.count() == 1
        assert recommendations[0].recommended == podcast_1
