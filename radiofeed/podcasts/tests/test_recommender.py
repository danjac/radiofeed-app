import pytest

from radiofeed.podcasts.models import Recommendation
from radiofeed.podcasts.recommender import get_categories, recommend
from radiofeed.podcasts.tests.factories import (
    create_category,
    create_podcast,
    create_recommendation,
)


@pytest.fixture()
def _clear_categories_cache():
    get_categories.cache_clear()
    return


class TestRecommender:
    @pytest.mark.django_db()
    @pytest.mark.usefixtures("_clear_categories_cache")
    def test_no_suitable_matches_for_podcasts(self):
        create_podcast(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )

        recommend("en")

        assert Recommendation.objects.count() == 0


class TestRecommend:
    @pytest.mark.django_db()
    @pytest.mark.usefixtures("_clear_categories_cache")
    def test_handle_empty_data_frame(self):
        create_podcast(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )

        recommend("en")
        assert Recommendation.objects.count() == 0

    @pytest.mark.django_db()
    @pytest.mark.usefixtures("_clear_categories_cache")
    def test_create_podcast_recommendations_with_no_categories(self):
        podcast_1 = create_podcast(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )
        create_podcast(
            title="Another cool science podcast",
            keywords="science physics astronomy",
        )
        create_podcast(title="Philosophy things", keywords="thinking")
        recommend("en")
        recommendations = (
            Recommendation.objects.filter(podcast=podcast_1)
            .order_by("similarity")
            .select_related("recommended")
        )
        assert recommendations.count() == 0

    @pytest.mark.django_db()
    @pytest.mark.usefixtures("_clear_categories_cache")
    def test_create_podcast_recommendations(self):
        cat_1 = create_category(name="Science")
        cat_2 = create_category(name="Philosophy")
        cat_3 = create_category(name="Culture")

        podcast_1 = create_podcast(
            extracted_text="Cool science podcast science physics astronomy",
            categories=[cat_1],
            title="podcast 1",
        )
        podcast_2 = create_podcast(
            extracted_text="Another cool science podcast science physics astronomy",
            categories=[cat_1, cat_2],
            title="podcast 2",
        )

        # ensure old recommendations are removed
        create_recommendation(
            podcast=podcast_1, recommended=create_podcast(title="podcast 4")
        )
        create_recommendation(
            podcast=podcast_2, recommended=create_podcast(title="podcast 5")
        )

        # must have at least one category in common
        create_podcast(
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
