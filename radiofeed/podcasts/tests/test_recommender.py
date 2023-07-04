from radiofeed.podcasts.models import Category, Podcast, Recommendation
from radiofeed.podcasts.recommender import Recommender, recommend
from radiofeed.podcasts.tests.factories import (
    create_category,
    create_podcast,
    create_recommendation,
)


class TestRecommender:
    def test_no_suitable_matches_for_podcasts(self, db):
        create_podcast(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )

        Recommender("en").recommend(Podcast.objects.none(), Category.objects.all())

        assert Recommendation.objects.count() == 0


class TestRecommend:
    def test_handle_empty_data_frame(self, db):
        create_podcast(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )

        recommend()
        assert Recommendation.objects.count() == 0

    def test_create_podcast_recommendations_with_no_categories(self, db):
        podcast_1 = create_podcast(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )
        create_podcast(
            title="Another cool science podcast",
            keywords="science physics astronomy",
        )
        create_podcast(title="Philosophy things", keywords="thinking")
        recommend()
        recommendations = (
            Recommendation.objects.filter(podcast=podcast_1)
            .order_by("similarity")
            .select_related("recommended")
        )
        assert recommendations.count() == 0

    def test_create_podcast_recommendations(self, db):
        cat_1 = create_category(name="Science")
        cat_2 = create_category(name="Philosophy")
        cat_3 = create_category(name="Culture")

        podcast_1 = create_podcast(
            extracted_text="Cool science podcast science physics astronomy",
            categories=[cat_1],
        )
        podcast_2 = create_podcast(
            extracted_text="Another cool science podcast science physics astronomy",
            categories=[cat_1, cat_2],
        )

        # ensure old recommendations are removed
        create_recommendation(podcast=podcast_1)
        create_recommendation(podcast=podcast_2)

        # must have at least one category in common
        create_podcast(
            extracted_text="Philosophy things thinking",
            categories=[cat_2, cat_3],
        )

        recommend()

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
