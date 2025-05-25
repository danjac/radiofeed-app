import functools
import itertools
from collections.abc import Iterator

import numpy as np
from django.db.models import QuerySet
from django.utils import timezone
from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer
from sklearn.neighbors import NearestNeighbors

from radiofeed import tokenizer
from radiofeed.podcasts.models import Category, Podcast, Recommendation


@functools.cache
def get_categories() -> list["Category"]:
    """Returns all categories from cache."""
    return list(Category.objects.all())


def recommend(language: str, **kwargs) -> None:
    """Generates Recommendation instances based on podcast similarity, grouped by
    language and category. Existing recommendations are first deleted."""
    _Recommender(language, **kwargs).recommend()


class _Recommender:
    def __init__(
        self,
        language: str,
        *,
        since: timezone.timedelta | None = None,
        num_matches: int = 12,
    ) -> None:
        self._language = language
        self._since = since or timezone.timedelta(days=90)
        self._num_matches = num_matches

    def recommend(self) -> None:
        # Delete existing recommendations for the language
        Recommendation.objects.filter(podcast__language=self._language).bulk_delete()

        for batch in itertools.batched(
            self._create_recommendations(),
            1000,
            strict=False,
        ):
            Recommendation.objects.bulk_create(batch, batch_size=100)

    def _create_recommendations(self) -> Iterator[Recommendation]:
        podcasts = Podcast.objects.filter(
            pub_date__gt=timezone.now() - self._since,
            language__iexact=self._language,
            active=True,
            private=False,
        ).exclude(extracted_text="")

        hasher = HashingVectorizer(
            stop_words=list(tokenizer.get_stopwords(self._language)),
            n_features=5000,
            alternate_sign=False,
        )

        corpus = podcasts.values_list("extracted_text", flat=True)

        try:
            counts = hasher.transform(corpus)
        except StopIteration:
            return

        transformer = TfidfTransformer()
        transformer.fit(counts)

        # Build matches across all categories

        matches = [
            category_matches
            for category in get_categories()
            for category_matches in self._matches_for_category(
                category,
                hasher,
                transformer,
                podcasts,
            )
            if category_matches
        ]

        if not matches:
            return

        matches = np.array(matches, dtype=object)

        podcast_ids = matches[:, 0].astype(int)
        recommended_ids = matches[:, 1].astype(int)
        similarities = matches[:, 2].astype(float)

        keys = np.stack((podcast_ids, recommended_ids), axis=1)
        unique_keys, inverse_indices = np.unique(keys, axis=0, return_inverse=True)

        for idx, (podcast_id, recommended_id) in enumerate(unique_keys):
            group_similarities = similarities[inverse_indices == idx]
            yield Recommendation(
                podcast_id=podcast_id,
                recommended_id=recommended_id,
                similarity=np.mean(group_similarities),
                frequency=group_similarities.size,
            )

    def _matches_for_category(
        self,
        category: Category,
        hasher: HashingVectorizer,
        transformer: TfidfTransformer,
        podcasts: QuerySet[Podcast],
    ) -> list[tuple[int, int, float]]:
        arr = np.array(
            podcasts.filter(categories=category).values_list(
                "id",
                "extracted_text",
            ),
            dtype=object,
        )

        if arr.size == 0:
            return []

        podcast_ids = arr[:, 0]
        texts = arr[:, 1]

        tfidf = transformer.transform(hasher.transform(texts))

        n_neighbors = min(self._num_matches, podcast_ids.size)

        nn = NearestNeighbors(
            n_neighbors=n_neighbors,
            metric="cosine",
            algorithm="brute",
        ).fit(tfidf)

        distances, indices = nn.kneighbors(tfidf)

        distances = distances[:, 1:]  # skip self
        indices = indices[:, 1:]  # skip self

        # remove any smilarities that are not positive
        similarities = 1 - distances
        mask = similarities > 0
        rows, cols = np.where(mask)

        podcast_ids_for_rows = podcast_ids[rows]

        recommended_indices = indices[rows, cols]
        recommended_ids = podcast_ids[recommended_indices]

        sim_values = similarities[rows, cols]

        return list(
            zip(
                podcast_ids_for_rows,
                recommended_ids,
                sim_values,
                strict=True,
            )
        )
