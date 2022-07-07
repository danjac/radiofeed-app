from radiofeed.podcasts.factories import CategoryFactory, PodcastFactory, RecommendationFactory
from radiofeed.podcasts.models import Category, Podcast, Recommendation
from radiofeed.podcasts.recommender import Recommender, recommend


class TestRecommender:
    def test_no_suitable_matches_for_podcasts(self, db):
        PodcastFactory(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )

        Recommender("en", 12).recommend(Podcast.objects.none(), Category.objects.all())

        assert Recommendation.objects.count() == 0


class TestRecommend:
    def test_handle_empty_data_frame(self, db):
        PodcastFactory(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )

        recommend()
        assert Recommendation.objects.count() == 0

    def test_create_podcast_recommendations_with_no_categories(self, db):
        podcast_1 = PodcastFactory(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )
        PodcastFactory(
            title="Another cool science podcast",
            keywords="science physics astronomy",
        )
        PodcastFactory(title="Philosophy things", keywords="thinking")
        recommend()
        recommendations = (
            Recommendation.objects.filter(podcast=podcast_1).order_by("similarity").select_related("recommended")
        )
        assert recommendations.count() == 0

    def test_create_podcast_recommendations(self, db):

        cat_1 = CategoryFactory(name="Science")
        cat_2 = CategoryFactory(name="Philosophy")
        cat_3 = CategoryFactory(name="Culture")

        podcast_1 = PodcastFactory(
            extracted_text="Cool science podcast science physics astronomy",
            categories=[cat_1],
        )
        podcast_2 = PodcastFactory(
            extracted_text="Another cool science podcast science physics astronomy",
            categories=[cat_1, cat_2],
        )

        # ensure old recommendations are removed
        RecommendationFactory(podcast=podcast_1)
        RecommendationFactory(podcast=podcast_2)

        # must have at least one category in common
        PodcastFactory(
            extracted_text="Philosophy things thinking",
            categories=[cat_2, cat_3],
        )

        recommend()

        recommendations = (
            Recommendation.objects.filter(podcast=podcast_1).order_by("similarity").select_related("recommended")
        )
        assert recommendations.count() == 1
        assert recommendations[0].recommended == podcast_2

        recommendations = (
            Recommendation.objects.filter(podcast=podcast_2).order_by("similarity").select_related("recommended")
        )
        assert recommendations.count() == 1
        assert recommendations[0].recommended == podcast_1
