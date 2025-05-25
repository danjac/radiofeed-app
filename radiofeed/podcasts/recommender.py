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
        batch_size: int = 100,
    ) -> None:
        self._language = language
        self._since = since or timezone.timedelta(days=90)
        self._num_matches = num_matches
        self._batch_size = batch_size

    def recommend(self) -> None:
        # Delete existing recommendations for the language
        Recommendation.objects.filter(podcast__language=self._language).bulk_delete()

        for batch in itertools.batched(
            self._create_recommendations(),
            self._batch_size,
            strict=False,
        ):
            Recommendation.objects.bulk_create(batch, batch_size=self._batch_size)

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
        matches = collections.defaultdict(list)

        for category in get_categories():
            for podcast_id, recommended_id, similarity in self._matches_for_category(
                category,
                hasher,
                transformer,
                podcasts,
            ):
                matches[(podcast_id, recommended_id)].append(similarity)

        if not matches:
            return

        for (podcast_id, recommended_id), similarities in matches.items():
            yield Recommendation(
                podcast_id=podcast_id,
                recommended_id=recommended_id,
                similarity=np.mean(similarities),
                frequency=len(similarities),
            )

    def _matches_for_category(
        self,
        category: Category,
        hasher: HashingVectorizer,
        transformer: TfidfTransformer,
        podcasts: QuerySet[Podcast],
    ) -> Iterator[tuple[int, int, float]]:
        try:
            podcast_ids, texts = zip(
                *podcasts.filter(categories=category).values_list(
                    "id",
                    "extracted_text",
                ),
                strict=True,
            )
        except ValueError:
            return

        tfidf = transformer.transform(hasher.transform(texts))

        n_neighbors = min(self._num_matches, len(podcast_ids))

        nn = NearestNeighbors(
            n_neighbors=n_neighbors,
            metric="cosine",
            algorithm="brute",
        ).fit(tfidf)

        distances, indices = nn.kneighbors(tfidf)

        for row_id, row_distances, row_indices in zip(
            podcast_ids,
            distances,
            indices,
            strict=True,
        ):
            for dist, idx in zip(
                row_distances[1:],
                row_indices[1:],
                strict=True,
            ):
                if (similarity := 1 - dist) > 0:
                    yield (row_id, podcast_ids[idx], similarity)
