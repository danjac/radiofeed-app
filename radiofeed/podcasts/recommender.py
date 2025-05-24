import collections
import functools
import itertools
import statistics
from collections.abc import Iterator

import numpy as np
from django.db.models import QuerySet
from django.utils import timezone
from sklearn.feature_extraction.text import (
    HashingVectorizer,
    TfidfTransformer,
)
from sklearn.neighbors import NearestNeighbors

from radiofeed import tokenizer
from radiofeed.podcasts.models import Category, Podcast, Recommendation


@functools.cache
def get_categories() -> list["Category"]:
    """Returns all categories from cache."""
    return list(Category.objects.all())


def recommend(language: str, **kwargs) -> None:
    """Generates Recommendation instances based on podcast similarity, grouped by
    language and category.

    Any existing recommendations are first deleted.

    Only podcasts matching certain languages and updated within the past 90 days are
    included.
    """
    _Recommender(language, **kwargs).recommend()


class _Recommender:
    """Creates recommendations for given language, based around text content and common
    categories."""

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
        """Creates recommendation instances."""

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

        # Transform corpus counts and fit TFIDF
        try:
            counts = hasher.transform(corpus)
        except StopIteration:
            return

        transformer = TfidfTransformer()
        transformer.fit(counts)

        # Delete existing recommendations first
        Recommendation.objects.filter(podcast__language=self._language).bulk_delete()

        for batch in itertools.batched(
            self._build_matches_dict(hasher, transformer, podcasts).items(),
            1000,
            strict=False,
        ):
            Recommendation.objects.bulk_create(
                (
                    Recommendation(
                        podcast_id=podcast_id,
                        recommended_id=recommended_id,
                        similarity=statistics.median(scores),
                        frequency=len(scores),
                    )
                    for (podcast_id, recommended_id), scores in batch
                ),
                batch_size=100,
                ignore_conflicts=True,
            )

    def _build_matches_dict(
        self,
        hasher: HashingVectorizer,
        transformer: TfidfTransformer,
        podcasts: QuerySet[Podcast],
    ) -> collections.defaultdict[tuple[int, int], list[float]]:
        matches: collections.defaultdict[tuple[int, int], list[float]] = (
            collections.defaultdict(list)
        )
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

        return matches

    def _find_matches_for_category(
        self,
        category: Category,
        hasher: HashingVectorizer,
        transformer: TfidfTransformer,
        podcasts: QuerySet[Podcast],
    ) -> Iterator[tuple[int, int, float]]:
        """Finds matches for the given podcasts based on their text content."""
        arr = np.array(
            podcasts.filter(categories=category).values_list(
                "id",
                "extracted_text",
            ),
            dtype=object,
        )  # shape (N, 2)

        if arr.size == 0:
            return

        podcast_ids = arr[:, 0]
        texts = arr[:, 1]

        x_counts = hasher.transform(texts)
        x_tfidf = transformer.transform(x_counts)

        n_neighbors = min(self._num_matches, podcast_ids.size)

        nn = NearestNeighbors(
            n_neighbors=n_neighbors,
            metric="cosine",
            algorithm="brute",
        ).fit(x_tfidf)

        distances, indices = nn.kneighbors(x_tfidf)

        # Skip self matches at index 0
        distances = distances[:, 1:]
        indices = indices[:, 1:]

        similarities = 1 - distances

        mask = similarities > 0
        rows, cols = np.where(mask)

        podcast_ids_for_rows = podcast_ids[rows]
        recommended_indices = indices[rows, cols]
        recommended_ids = podcast_ids[recommended_indices]

        sim_values = similarities[rows, cols]

        results = np.column_stack((podcast_ids_for_rows, recommended_ids, sim_values))
        for podcast_id, recommended_id, sim in results:
            yield int(podcast_id), int(recommended_id), float(sim)
