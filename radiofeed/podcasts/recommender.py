import collections
import itertools
import operator
import statistics
from collections.abc import Iterator
from datetime import timedelta

from django.db.models import QuerySet
from django.db.models.functions import Lower
from django.utils import timezone
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from radiofeed import iterators, tokenizer
from radiofeed.podcasts.models import Category, Podcast, Recommendation


def recommend() -> None:
    """Generates Recommendation instances based on podcast similarity, grouped by
    language and category.

    Any existing recommendations are first deleted.

    Only podcasts matching certain languages and updated within the past 90 days are
    included.
    """
    podcasts = (
        Podcast.objects.filter(
            pub_date__gt=timezone.now() - timedelta(days=90),
            active=True,
            private=False,
        )
        .filter(language__in=tokenizer.NLTK_LANGUAGES)
        .exclude(extracted_text="")
    )

    categories = Category.objects.order_by("name")

    # separate by language, so we don't get false matches

    for language in podcasts.values_list(Lower("language"), flat=True).distinct():
        Recommender(language).recommend(podcasts, categories)


class Recommender:
    """Creates recommendations for given language, based around text content and common
    categories."""

    _num_matches: int = 12

    def __init__(self, language: str):
        self._language = language

        self._vectorizer = HashingVectorizer(
            stop_words=list(tokenizer.get_stopwords(self._language))
        )

    def recommend(
        self, podcasts: QuerySet[Podcast], categories: QuerySet[Category]
    ) -> None:
        """Creates recommendation instances."""
        # Delete existing recommendations first
        Recommendation.objects.filter(podcast__language=self._language).bulk_delete()

        for batch in iterators.batcher(
            self._build_matches_dict(
                podcasts.filter(language=self._language), categories
            ).items(),
            1000,
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
        self, podcasts: QuerySet[Podcast], categories: QuerySet[Category]
    ) -> collections.defaultdict[tuple[int, int], list[float]]:
        matches = collections.defaultdict(list)

        for category in categories:
            for batch in iterators.batcher(
                podcasts.filter(categories=category)
                .values_list("id", "extracted_text")
                .iterator(),
                1000,
            ):
                for (
                    podcast_id,
                    recommended_id,
                    similarity,
                ) in self._find_similarities(dict(batch)):
                    matches[(podcast_id, recommended_id)].append(similarity)

        return matches

    def _find_similarities(
        self, rows: dict[int, str]
    ) -> Iterator[tuple[int, int, float]]:
        # build a data model of podcasts with same language and category

        if not rows:
            return  # pragma: no cover

        try:
            cosine_sim = cosine_similarity(self._vectorizer.transform(rows.values()))
        except ValueError:  # pragma: no cover
            return

        podcast_ids = list(rows.keys())

        for current_id, similar in zip(podcast_ids, cosine_sim, strict=True):
            try:
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

            except IndexError:  # pragma: no cover
                continue
