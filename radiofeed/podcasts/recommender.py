import collections
import contextlib
import itertools
import operator
import statistics
from collections.abc import Iterator

from django.db.models import QuerySet
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from radiofeed import tokenizer
from radiofeed.podcasts.models import Category, Podcast, Recommendation


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
        max_features: int = 5000,
    ) -> None:
        self._language = language
        self._since = since or timezone.timedelta(days=90)
        self._num_matches = num_matches

        self._vectorizer = TfidfVectorizer(
            stop_words=list(tokenizer.get_stopwords(self._language)),
            max_features=max_features,
        )

    def recommend(self) -> None:
        """Creates recommendation instances."""

        # Delete existing recommendations first
        Recommendation.objects.filter(podcast__language=self._language).bulk_delete()

        for batch in itertools.batched(
            self._build_matches_dict().items(),
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
    ) -> collections.defaultdict[tuple[int, int], list[float]]:
        matches = collections.defaultdict(list)

        for category in Category.objects.from_cache():
            for batch in itertools.batched(
                self._get_podcasts(category)
                .values_list("id", "extracted_text")
                .iterator(),
                1000,
                strict=False,
            ):
                for (
                    podcast_id,
                    recommended_id,
                    similarity,
                ) in self._find_similarities(dict(batch)):
                    matches[podcast_id, recommended_id].append(similarity)

        return matches

    def _get_podcasts(self, category: Category) -> QuerySet[Podcast]:
        return Podcast.objects.filter(
            pub_date__gt=timezone.now() - self._since,
            language__iexact=self._language,
            categories=category,
            active=True,
            private=False,
        ).exclude(extracted_text="")

    def _find_similarities(
        self, rows: dict[int, str]
    ) -> Iterator[tuple[int, int, float]]:
        # build a data model of podcasts with same language and category

        with contextlib.suppress(ValueError):
            cosine_sim = cosine_similarity(
                self._vectorizer.fit_transform(rows.values())
            )

            podcast_ids = list(rows.keys())

            for current_id, similar in zip(podcast_ids, cosine_sim, strict=True):
                with contextlib.suppress(IndexError):
                    for index, similarity in itertools.islice(
                        sorted(
                            enumerate(similar),
                            key=operator.itemgetter(1),
                            reverse=True,
                        ),
                        self._num_matches,
                    ):
                        if (
                            similarity > 0
                            and (recommended_id := podcast_ids[index]) != current_id
                        ):
                            yield current_id, recommended_id, similarity
