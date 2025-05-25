import collections
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

        corpus = podcasts.values_list("extracted_text", flat=True)

        hasher = HashingVectorizer(
            stop_words=list(tokenizer.get_stopwords(self._language)),
            n_features=5000,
            alternate_sign=False,
        )

        try:
            counts = hasher.transform(corpus)
        except StopIteration:
            return

        transformer = TfidfTransformer()
        transformer.fit(counts)

        matches = collections.defaultdict(list)

        for category in get_categories():
            for (
                podcast_id,
                recommended_id,
                similarity,
            ) in self._find_matches_for_category(
                category,
                hasher,
                transformer,
                podcasts,
            ):
                matches[(podcast_id, recommended_id)].append(similarity)

        for (podcast_id, recommended_id), similarities in matches.items():
            yield Recommendation(
                podcast_id=podcast_id,
                recommended_id=recommended_id,
                similarity=np.median(similarities),
                frequency=len(similarities),
            )

    def _find_matches_for_category(
        self,
        category: Category,
        hasher: HashingVectorizer,
        transformer: TfidfTransformer,
        podcasts: QuerySet[Podcast],
    ) -> np.ndarray:
        arr = np.array(
            podcasts.filter(categories=category).values_list(
                "id",
                "extracted_text",
            ),
            dtype=object,
        )

        if arr.size == 0:
            return arr

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

        # Skip self-matches
        distances = distances[:, 1:]
        indices = indices[:, 1:]

        similarities = 1 - distances
        mask = similarities > 0
        rows, cols = np.where(mask)

        podcast_ids_for_rows = podcast_ids[rows]
        recommended_indices = indices[rows, cols]
        recommended_ids = podcast_ids[recommended_indices]
        sim_values = similarities[rows, cols]

        return np.column_stack(
            (
                podcast_ids_for_rows,
                recommended_ids,
                sim_values,
            )
        )
