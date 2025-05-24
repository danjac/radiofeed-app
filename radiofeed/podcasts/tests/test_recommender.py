import pytest
from sklearn.feature_extraction.text import (
    HashingVectorizer,
    TfidfTransformer,
)

from radiofeed.podcasts.models import Category, Podcast, Recommendation
from radiofeed.podcasts.recommender import _Recommender, get_categories, recommend
from radiofeed.podcasts.tests.factories import (
    PodcastFactory,
    RecommendationFactory,
)


class TestRecommender:
    @pytest.fixture(autouse=True)
    def clear_categories_cache(self):
        # ensure fresh category list each time
        get_categories.cache_clear()

    @pytest.mark.django_db
    def test_no_suitable_matches_for_podcasts(self):
        # must provide extracted_text and language, since the new logic filters on these
        PodcastFactory(
            title="Cool science podcast",
            extracted_text="science physics astronomy",
            language="en",
        )

        recommend("en")
        assert Recommendation.objects.count() == 0


class TestRecommend:
    @pytest.fixture(autouse=True)
    def clear_categories_cache(self):
        get_categories.cache_clear()

    @pytest.mark.django_db
    def test_recommend_with_no_podcasts(self):
        # No podcasts inserted, corpus is empty
        recommend("en")  # Should handle empty corpus without exception
        assert Recommendation.objects.count() == 0

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
    def test_create_recommendations(self):
        # set up categories
        Category.objects.bulk_create(
            [Category(name=n) for n in ("Science", "Philosophy", "Society & Culture")],
            ignore_conflicts=True,
        )
        cat_1 = Category.objects.get(name="Science")
        cat_2 = Category.objects.get(name="Philosophy")
        cat_3 = Category.objects.get(name="Society & Culture")

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
        assert recs_1.first().recommended == podcast_2

        # podcast_2 should recommend podcast_1 as well
        recs_2 = Recommendation.objects.filter(podcast=podcast_2)
        assert recs_2.count() == 1
        assert recs_2.first().recommended == podcast_1

    @pytest.mark.django_db
    def test_find_matches_for_category_empty_queryset(self):
        # Create a category with no podcasts assigned
        empty_category = Category.objects.create(name="EmptyCategory")

        # Make sure at least one podcast exists, but not in empty_category
        PodcastFactory(categories=[])

        recommender = _Recommender(language="en")

        hasher = HashingVectorizer(
            stop_words=[],
            n_features=5000,
            alternate_sign=False,
        )
        transformer = TfidfTransformer()

        # forcibly call _find_matches_for_category on empty_category, should handle ValueError and return empty
        matches = list(
            recommender._find_matches_for_category(
                empty_category,
                hasher,
                transformer,
                Podcast.objects.all(),
            )
        )
        assert matches == []

    @pytest.mark.django_db
    def test_find_matches_for_category_single_podcast_returns_empty(self):
        category = Category.objects.create(name="SoloCategory")
        PodcastFactory(categories=[category])

        hasher = HashingVectorizer(
            stop_words=[],
            n_features=5000,
            alternate_sign=False,
        )
        transformer = TfidfTransformer()

        # Fit transformer with dummy data so it is ready
        sample_texts = ["dummy text one", "dummy text two"]
        counts = hasher.transform(sample_texts)
        transformer.fit(counts)

        recommender = _Recommender(language="en")

        matches = list(
            recommender._find_matches_for_category(
                category,
                hasher,
                transformer,
                Podcast.objects.filter(categories=category),
            )
        )
        assert matches == []
