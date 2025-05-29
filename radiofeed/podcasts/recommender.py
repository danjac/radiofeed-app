import collections
import dataclasses
import itertools
import statistics
from collections.abc import Iterator
from typing import Final

import numpy as np
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils import timezone
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import (
    HashingVectorizer,
    TfidfTransformer,
)
from sklearn.neighbors import NearestNeighbors

from radiofeed.podcasts.models import Podcast, Recommendation

_default_timeframe: Final = timezone.timedelta(days=90)

_transformer = TfidfTransformer()
_hasher = HashingVectorizer(n_features=30000, alternate_sign=False)


def recommend(
    language: str,
    *,
    timeframe: timezone.timedelta | None = None,
    num_matches: int = 12,
    batch_size: int = 100,
) -> None:
    """Generates Recommendation instances based on podcast similarity, grouped by
    language and category. Existing recommendations are first deleted."""

    Recommendation.objects.filter(podcast__language__iexact=language).bulk_delete()

    recommender = _Recommender(
        language=language,
        timeframe=timeframe or _default_timeframe,
        num_matches=num_matches,
    )

    for batch in itertools.batched(
        recommender.recommend(),
        batch_size,
        strict=False,
    ):
        Recommendation.objects.bulk_create(batch)


@dataclasses.dataclass(frozen=True, kw_only=True)
class _Recommender:
    language: str
    num_matches: int
    timeframe: timezone.timedelta

    def recommend(self) -> Iterator[Recommendation]:
        """Build Recommendation instances based on podcast similarity, grouped by category."""
        matches = collections.defaultdict(list)

        for podcast_id, recommended_id, similarity in self._find_similarities():
            matches[(podcast_id, recommended_id)].append(similarity)

        for (podcast_id, recommended_id), similarities in matches.items():
            yield Recommendation(
                podcast_id=podcast_id,
                recommended_id=recommended_id,
                score=self._calculate_score(similarities),
            )

    def _find_similarities(self) -> Iterator[tuple[int, int, float]]:
        podcast_ids, corpus, categories = self._build_dataset()

        if not podcast_ids or not corpus or not categories:
            return

        podcast_index = {podcast_id: idx for idx, podcast_id in enumerate(podcast_ids)}

        tfidf_matrix = _transformer.fit_transform(_hasher.transform(corpus))

        for category_podcast_ids in categories.values():
            indices = [
                podcast_index[podcast_id]
                for podcast_id in category_podcast_ids
                if podcast_id in podcast_index
            ]

            yield from self._find_nearest_neighbours(tfidf_matrix, indices, podcast_ids)

    def _calculate_score(self, values: list[float]) -> float:
        return len(values) * statistics.mean(values)

    def _build_dataset(self) -> tuple[list[int], list[str], dict[int, set[int]]]:
        podcast_ids = []
        corpus = []

        categories = collections.defaultdict(set)

        for podcast_id, text, category_ids in self._get_queryset():
            podcast_ids.append(podcast_id)
            corpus.append(text)

            for category_id in category_ids:
                categories[category_id].add(podcast_id)

        return podcast_ids, corpus, categories

    def _find_nearest_neighbours(
        self,
        tfidf_matrix: csr_matrix,
        indices: list[int],
        podcast_ids: list[int],
    ) -> Iterator[tuple[int, int, float]]:
        subset_ids = np.array([podcast_ids[idx] for idx in indices])
        n_neighbors = min(self.num_matches, len(subset_ids))

        tfidf_subset = tfidf_matrix[indices]

        nn = NearestNeighbors(
            n_neighbors=n_neighbors,
            metric="cosine",
            algorithm="brute",
        ).fit(tfidf_subset)

        distances, neighbors = nn.kneighbors(tfidf_subset)

        # Exclude self-match in first column
        similarities = 1 - distances[:, 1:]
        filtered_neighbors = neighbors[:, 1:]

        # Filter for positive similarity only
        mask = similarities > 0
        row_idxs, col_idxs = np.where(mask)

        row_ids = subset_ids[row_idxs]
        neighbor_ids = subset_ids[filtered_neighbors[row_idxs, col_idxs]]
        sims = similarities[row_idxs, col_idxs]

        return zip(row_ids, neighbor_ids, sims, strict=True)

    def _get_queryset(self) -> QuerySet:
        return (
            Podcast.objects.annotate(
                category_ids=ArrayAgg(
                    "categories__id",
                    filter=~Q(
                        categories__pk=None,
                    ),
                    distinct=True,
                ),
            )
            .filter(
                category_ids__len__gt=0,
                pub_date__gt=timezone.now() - self.timeframe,
                language__iexact=self.language,
                active=True,
                private=False,
            )
            .exclude(extracted_text="")
            .values_list(
                "id",
                "extracted_text",
                "category_ids",
            )
        )
