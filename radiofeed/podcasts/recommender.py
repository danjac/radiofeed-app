import collections
import itertools
import statistics
from collections.abc import Iterator

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q, QuerySet
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
    _batch_size: int = 100
    _n_features: int = 3000

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
            self._batch_size,
            strict=False,
        ):
            Recommendation.objects.bulk_create(batch)

    def _create_recommendations(self) -> Iterator[Recommendation]:
        queryset = self._get_queryset()

        podcast_ids = []
        corpus = []

        categories_map = collections.defaultdict(set)

        for podcast_id, text, categories in queryset.values_list(
            "id",
            "extracted_text",
            "category_ids",
        ):
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
                similarity=statistics.mean(similarities),
                frequency=len(similarities),
            )

    def _get_queryset(self) -> QuerySet[Podcast]:
        # Return active public podcasts within timeframe that have at least one category
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
                id_to_index[pid] for pid in category_podcast_ids if pid in id_to_index
            ]

            tfidf_subset = tfidf_matrix[indices]
            subset_ids = [podcast_ids[i] for i in indices]

            n_neighbors = min(self._num_matches, len(subset_ids))

            nn = NearestNeighbors(
                n_neighbors=n_neighbors,
                metric="cosine",
                algorithm="brute",
            ).fit(tfidf_subset)

            distances, neighbors = nn.kneighbors(tfidf_subset)

            for row_id, row_distances, row_indices in zip(
                subset_ids,
                distances,
                neighbors,
                strict=True,
            ):
                for dist, idx in zip(
                    row_distances[1:],
                    row_indices[1:],
                    strict=True,
                ):
                    similarity = 1 - dist
                    if similarity > 0:
                        yield row_id, subset_ids[idx], similarity
