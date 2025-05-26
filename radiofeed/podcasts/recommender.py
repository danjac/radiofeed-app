import collections
import itertools
import statistics
from collections.abc import Iterator

from django.utils import timezone
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer
from sklearn.neighbors import NearestNeighbors

from radiofeed import tokenizer
from radiofeed.podcasts.models import Podcast, Recommendation


def recommend(language: str, **kwargs) -> None:
    """Generates Recommendation instances based on podcast similarity, grouped by
    language and category. Existing recommendations are first deleted."""
    _Recommender(language, **kwargs).recommend()


class _Recommender:
    batch_size: int = 100
    n_features: int = 3000

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
            self.batch_size,
            strict=False,
        ):
            Recommendation.objects.bulk_create(batch, batch_size=self.batch_size)

    def _create_recommendations(self) -> Iterator[Recommendation]:
        queryset = Podcast.objects.filter(
            pub_date__gt=timezone.now() - self._since,
            language__iexact=self._language,
            active=True,
            private=False,
        ).exclude(extracted_text="")

        try:
            podcast_ids, corpus = zip(
                *queryset.values_list("id", "extracted_text"),
                strict=True,
            )
        except ValueError:
            return

        categories_map = collections.defaultdict(set)

        for podcast_id, category_id in Podcast.categories.through.objects.filter(
            podcast_id__in=podcast_ids
        ).values_list("podcast_id", "category_id"):
            categories_map[category_id].add(podcast_id)

        if not categories_map:
            return

        hasher = HashingVectorizer(
            stop_words=list(tokenizer.get_stopwords(self._language)),
            n_features=self.n_features,
            alternate_sign=False,
        )

        tfidf_matrix = TfidfTransformer().fit_transform(hasher.transform(corpus))

        matches = collections.defaultdict(list)

        for podcast_id, recommended_id, similarity in self._build_matches_by_category(
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

    def _build_matches_by_category(
        self,
        tfidf_matrix: csr_matrix,
        podcast_ids: tuple[int, ...],
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
