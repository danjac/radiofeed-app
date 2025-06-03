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


@dataclasses.dataclass(frozen=True)
class _DataSet:
    podcast_ids: list[int]
    corpus: list[str]
    categories: dict[int, set[int]]
    category_sizes: collections.Counter

    def empty(self) -> bool:
        return not self.podcast_ids or not self.corpus or not self.categories


@dataclasses.dataclass(frozen=True, kw_only=True)
class _Recommender:
    language: str
    num_matches: int
    timeframe: timezone.timedelta

    def recommend(self) -> Iterator[Recommendation]:
        """Build Recommendation instances based on podcast similarity, grouped by category."""
        dataset = self._build_dataset()

        if dataset.empty():
            return

        matches = collections.defaultdict(list)

        for (
            podcast_id,
            recommended_id,
            similarity,
            category_id,
        ) in self._find_similarities(dataset):
            matches[(podcast_id, recommended_id)].append((similarity, category_id))

        for (podcast_id, recommended_id), values in matches.items():
            yield Recommendation(
                podcast_id=podcast_id,
                recommended_id=recommended_id,
                score=self._calculate_score(values, dataset),
            )

    def _find_similarities(
        self, dataset: _DataSet
    ) -> Iterator[tuple[int, int, float, int]]:
        podcast_index = {pid: idx for idx, pid in enumerate(dataset.podcast_ids)}
        tfidf_matrix = _transformer.fit_transform(_hasher.transform(dataset.corpus))

        for category_id, category_podcast_ids in dataset.categories.items():
            indices = [
                podcast_index[pid]
                for pid in category_podcast_ids
                if pid in podcast_index
            ]

            subset_ids = np.array([dataset.podcast_ids[idx] for idx in indices])
            n_neighbors = min(self.num_matches, len(subset_ids))

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

            yield from zip(
                row_ids,
                neighbor_ids,
                sims,
                itertools.repeat(category_id, len(row_ids)),
                strict=True,
            )

    def _calculate_score(
        self,
        values: list[tuple[float, int]],
        dataset: _DataSet,
    ) -> float:
        """Compute recommendation score adjusted by category size."""
        scores = []
        for similarity, category_id in values:
            category_size = dataset.category_sizes.get(category_id, 1)
            adjusted = similarity / category_size
            scores.append(adjusted)
        return len(values) * statistics.mean(scores)

    def _build_dataset(self) -> _DataSet:
        podcast_ids: list[int] = []
        corpus: list[str] = []
        categories: dict[int, set[int]] = collections.defaultdict(set)
        category_sizes: collections.Counter = collections.Counter()

        for podcast_id, text, category_ids in self._get_queryset():
            podcast_ids.append(podcast_id)
            corpus.append(text)

            for category_id in category_ids:
                categories[category_id].add(podcast_id)
                category_sizes[category_id] += 1

        return _DataSet(
            podcast_ids=podcast_ids,
            corpus=corpus,
            categories=categories,
            category_sizes=category_sizes,
        )

    def _get_queryset(self) -> QuerySet:
        return (
            Podcast.objects.annotate(
                category_ids=ArrayAgg(
                    "categories__id",
                    filter=~Q(categories__pk=None),
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
            .values_list("id", "extracted_text", "category_ids")
        )
