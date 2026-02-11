import pytest

from radiofeed.podcasts.models import Category, Recommendation
from radiofeed.podcasts.recommender import recommend
from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
)


class TestRecommend:
    @pytest.mark.django_db
    def test_recommend_with_no_podcasts(self):
        # No podcasts inserted, corpus is empty
        recommend("en")  # Should handle empty corpus without exception
        assert Recommendation.objects.exists() is False

    @pytest.mark.django_db
    def test_podcast_never_recommends_itself(self):
        # set up a shared category
        cat = CategoryFactory.create()

        # create multiple podcasts in the same category
        podcasts = PodcastFactory.create_batch(
            3,
            extracted_text="shared content about science and tech",
            language="en",
            categories=[cat],
        )

        recommend("en")

        for podcast in podcasts:
            recs = Recommendation.objects.filter(podcast=podcast)
            assert recs.count() > 0
            # The podcast itself should never appear in its recommendations
            assert all(r.recommended != podcast for r in recs)

    @pytest.mark.django_db
    def test_handle_empty_data_frame(self):
        PodcastFactory(
            title="Cool science podcast",
            extracted_text="science physics astronomy",
            language="en",
        )

        recommend("en")
        assert Recommendation.objects.count() == 0

    @pytest.mark.django_db
    def test_no_categories(self):
        podcast_1 = PodcastFactory(
            title="Cool science podcast",
            extracted_text="science physics astronomy",
            language="en",
        )
        PodcastFactory(
            title="Another cool science podcast",
            extracted_text="science physics astronomy",
            language="en",
        )
        PodcastFactory(
            title="Philosophy things",
            extracted_text="thinking",
            language="en",
        )

        recommend("en")
        # no common category, so still zero recommendations
        assert Recommendation.objects.filter(podcast=podcast_1).count() == 0

    @pytest.mark.django_db
    def test_create_podcast_recommendations(self):
        # set up categories
        cat_1, cat_2, cat_3 = CategoryFactory.create_batch(3)

        # two science podcasts share cat_1
        podcast_1 = PodcastFactory(
            title="podcast 1",
            extracted_text="Cool science podcast science physics astronomy",
            language="en",
            categories=[cat_1],
        )
        podcast_2 = PodcastFactory(
            title="podcast 2",
            extracted_text="Another cool science podcast science physics astronomy",
            language="en",
            categories=[cat_1, cat_2],
        )

        # old recommendations should be cleaned up
        RecommendationFactory(
            podcast=podcast_1,
            recommended=PodcastFactory(
                title="podcast old", extracted_text="old", language="en"
            ),
        )
        RecommendationFactory(
            podcast=podcast_2,
            recommended=PodcastFactory(
                title="podcast old2", extracted_text="old2", language="en"
            ),
        )

        # a third podcast sharing only Philosophy (cat_2)
        PodcastFactory(
            title="podcast 3",
            extracted_text="Philosophy things thinking",
            language="en",
            categories=[cat_2, cat_3],
        )

        recommend("en")

        # podcast_1 should recommend podcast_2 (only shared category = Science)
        recs_1 = Recommendation.objects.filter(podcast=podcast_1)
        assert recs_1.count() == 1
        assert recs_1.get().recommended == podcast_2

        # podcast_2 should recommend podcast_1 as well
        recs_2 = Recommendation.objects.filter(podcast=podcast_2)
        assert recs_2.count() == 1
        assert recs_2.get().recommended == podcast_1

    @pytest.mark.django_db
    def test_one_podcast(self):
        # set up categories
        cat = CategoryFactory()

        # two science podcasts share cat_1
        PodcastFactory(
            title="podcast 1",
            extracted_text="Cool science podcast science physics astronomy",
            language="en",
            categories=[cat],
        )

        recommend("en")

        assert Recommendation.objects.exists() is False

    @pytest.mark.django_db
    def test_matches_for_category_empty_queryset(self):
        # Create a category with no podcasts assigned
        Category.objects.create(name="EmptyCategory")

        # Make sure at least one podcast exists, but not in empty_category
        PodcastFactory(
            title="podcast 3",
            extracted_text="Philosophy things thinking",
            language="en",
        )

        recommend("en")

        assert Recommendation.objects.exists() is False
