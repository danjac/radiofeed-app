import collections
import statistics
from collections.abc import Iterator

import numpy as np
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils import timezone
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer
from sklearn.neighbors import NearestNeighbors

from radiofeed.podcasts.models import Podcast, Recommendation


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
        n_features: int = 30000,
    ) -> None:
        self._language = language
        self._since = since or timezone.timedelta(days=90)
        self._num_matches = num_matches
        self._n_features = n_features

    def recommend(self) -> list[Recommendation]:
        """Generates recommendations for podcasts in the specified language."""

        Recommendation.objects.filter(
            podcast__language__iexact=self._language
        ).bulk_delete()

        return Recommendation.objects.bulk_create(
            self._create_recommendations(self._get_queryset())
        )

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
                pub_date__gt=timezone.now() - self._since,
                language__iexact=self._language,
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

    def _create_recommendations(self, queryset: QuerySet) -> Iterator[Recommendation]:
        podcast_ids = []
        corpus = []

        categories_map = collections.defaultdict(set)

        for podcast_id, text, categories in queryset:
            podcast_ids.append(podcast_id)
            corpus.append(text)

            for category_id in categories:
                categories_map[category_id].add(podcast_id)

        if not podcast_ids:
            return

        hasher = HashingVectorizer(n_features=self._n_features, alternate_sign=False)
        tfidf_matrix = TfidfTransformer().fit_transform(hasher.transform(corpus))

        matches = collections.defaultdict(list)

        for podcast_id, recommended_id, similarity in self._matches_by_category(
            tfidf_matrix,
            podcast_ids,
            categories_map,
        ):
            matches[(podcast_id, recommended_id)].append(similarity)

        for (podcast_id, recommended_id), similarities in matches.items():
            yield Recommendation(
                podcast_id=podcast_id,
                recommended_id=recommended_id,
                score=len(similarities) * statistics.mean(similarities),
            )

    def _matches_by_category(
        self,
        tfidf_matrix: csr_matrix,
        podcast_ids: list[int],
        categories_map: dict[int, set[int]],
    ) -> Iterator[tuple[int, int, float]]:
        id_to_index = {podcast_id: idx for idx, podcast_id in enumerate(podcast_ids)}

        for category_podcast_ids in categories_map.values():
            indices = [
                id_to_index[podcast_id]
                for podcast_id in category_podcast_ids
                if podcast_id in id_to_index
            ]

            tfidf_subset = tfidf_matrix[indices]
            subset_ids = np.array([podcast_ids[idx] for idx in indices])

            n_neighbors = min(self._num_matches, len(subset_ids))

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

            yield from zip(row_ids, neighbor_ids, sims, strict=True)
