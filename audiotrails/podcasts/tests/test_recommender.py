import pytest

from ..factories import CategoryFactory, PodcastFactory, RecommendationFactory
from ..models import Recommendation
from ..recommender import recommend
from ..recommender.text_parser import clean_text, extract_keywords

pytestmark = pytest.mark.django_db


class TestPodcastRecommender:
    def test_handle_empty_data_frame(self):
        PodcastFactory(
            title="Cool science podcast",
            keywords="science physics astronomy",
            pub_date=None,
        )

        recommend()
        assert Recommendation.objects.count() == 0

    def test_create_podcast_recommendations_with_no_categories(self):
        podcast_1 = PodcastFactory(
            title="Cool science podcast",
            keywords="science physics astronomy",
        )
        PodcastFactory(
            title="Another cool science podcast",
            keywords="science physics astronomy",
        )
        PodcastFactory(
            title="Philosophy things",
            keywords="thinking",
        )
        recommend()
        recommendations = (
            Recommendation.objects.filter(podcast=podcast_1)
            .order_by("similarity")
            .select_related("recommended")
        )
        assert recommendations.count() == 0

    def test_create_podcast_recommendations(self):

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
            Recommendation.objects.filter(podcast=podcast_1)
            .order_by("similarity")
            .select_related("recommended")
        )
        assert recommendations.count() == 1
        assert recommendations[0].recommended == podcast_2


class TestExtractKeywords:
    def test_extract(self):
        assert extract_keywords("en", "the cat sits on the mat") == [
            "cat",
            "sits",
            "mat",
        ]


class TestCleanText:
    def test_remove_html_tags(self):
        assert clean_text("<p>test</p>") == "test"

    def test_remove_numbers(self):
        assert clean_text("Tuesday, September 1st, 2020") == "Tuesday September st "
