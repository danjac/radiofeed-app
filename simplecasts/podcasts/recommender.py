import collections
import itertools
import math
import statistics
from collections.abc import Iterator
from datetime import timedelta
from typing import Final

import numpy as np
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils import timezone
from sklearn.feature_extraction.text import (
    HashingVectorizer,
    TfidfTransformer,
)
from sklearn.neighbors import NearestNeighbors

from simplecasts.podcasts.models import Podcast, Recommendation

_default_timeframe: Final = timedelta(days=90)

_transformer = TfidfTransformer()
_hasher = HashingVectorizer(n_features=30000, alternate_sign=False)


def recommend(
    language: str,
    *,
    timeframe: timedelta | None = None,
    num_matches: int = 12,
) -> None:
    """Generates Recommendation instances based on podcast similarity, grouped by
    language and category. Existing recommendations are first deleted."""

    Recommendation.objects.filter(podcast__language__iexact=language).bulk_delete()

    recommender = _Recommender(
        language=language,
        timeframe=timeframe or _default_timeframe,
        num_matches=num_matches,
    )

    Recommendation.objects.bulk_create(recommender.recommend())


class _Recommender:
    def __init__(
        self,
        *,
        language: str,
        timeframe: timedelta,
        num_matches: int,
    ) -> None:
        self._language = language
        self._timeframe = timeframe
        self._num_matches = num_matches

    def recommend(self) -> Iterator[Recommendation]:
        """Build Recommendation instances based on podcast similarity, grouped by category."""

        # Build the corpus and category mappings
        self._build_dataset()

        # If there are no categories, there is nothing to do
        if not self._categories:
            return

        # Find similarities and group them by (podcast_id, recommended_id)
        matches = collections.defaultdict(list)

        for (
            podcast_id,
            recommended_id,
            similarity,
            category_id,
        ) in self._find_similarities():
            matches[(podcast_id, recommended_id)].append((similarity, category_id))

        # Create Recommendation instances with calculated scores
        for (podcast_id, recommended_id), values in matches.items():
            yield Recommendation(
                podcast_id=podcast_id,
                recommended_id=recommended_id,
                score=self._calculate_score(values),
            )

    def _build_dataset(self) -> None:
        # Build podcast index and corpus
        self._podcast_index: dict[int, int] = {}
        self._corpus: list[str] = []

        self._categories = collections.defaultdict(set)
        self._category_sizes = collections.Counter()

        for counter, (podcast_id, text, category_ids) in enumerate(
            self._get_queryset()
        ):
            self._podcast_index[podcast_id] = counter
            self._corpus.append(text)

            for category_id in category_ids:
                self._categories[category_id].add(podcast_id)
                self._category_sizes[category_id] += 1

    def _get_queryset(self) -> QuerySet:
        # Retrieve podcasts with their categories for the specified language and timeframe
        return (
            Podcast.objects.annotate(
                category_ids=ArrayAgg(
                    "categories__id",
                    filter=~Q(categories__pk=None),
                    distinct=True,
                ),
            )
            .filter(
                language__iexact=self._language,
                pub_date__gt=timezone.now() - self._timeframe,
                category_ids__len__gt=0,
                active=True,
                private=False,
            )
            .exclude(extracted_text="")
            .values_list("id", "extracted_text", "category_ids")
        )

    def _find_similarities(self) -> Iterator[tuple[int, int, float, int]]:
        # Transform the corpus into TF-IDF matrix
        tfidf_matrix = _transformer.fit_transform(_hasher.transform(self._corpus))
        podcast_ids = list(self._podcast_index.keys())

        for category_id, category_podcast_ids in self._categories.items():
            indices = [
                self._podcast_index[pid]
                for pid in category_podcast_ids
                if pid in self._podcast_index
            ]

            subset_ids = np.array([podcast_ids[idx] for idx in indices])
            n_neighbors = min(self._num_matches, len(subset_ids))

            if n_neighbors <= 1:
                continue

            tfidf_subset = tfidf_matrix[indices]

            nn = NearestNeighbors(
                n_neighbors=n_neighbors,
                metric="cosine",
                algorithm="brute",
            ).fit(tfidf_subset)

            distances, neighbors = nn.kneighbors(tfidf_subset)

            similarities = 1 - distances[:, 1:]
            filtered_neighbors = neighbors[:, 1:]

            mask = similarities > 0
            row_idxs, col_idxs = np.where(mask)

            row_ids = subset_ids[row_idxs]
            neighbor_ids = subset_ids[filtered_neighbors[row_idxs, col_idxs]]
            sims = similarities[row_idxs, col_idxs]

            # remove zero similarity and self-references
            mask = (row_ids != neighbor_ids) & (sims > 0)
            row_ids = row_ids[mask]
            neighbor_ids = neighbor_ids[mask]
            sims = sims[mask]

            yield from zip(
                row_ids,
                neighbor_ids,
                sims,
                itertools.repeat(category_id, len(row_ids)),
                strict=True,
            )

    def _calculate_score(self, values: list[tuple[float, int]]) -> float:
        # Calculate weighted score based on similarities and category sizes
        scores = []
        for similarity, category_id in values:
            size = self._category_sizes.get(category_id, 1)
            weight = 1 / (1 + math.log(size))
            scores.append(similarity * weight)

        return len(scores) * statistics.mean(scores)
