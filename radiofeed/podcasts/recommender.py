from __future__ import annotations

import collections
import logging
import operator

from collections.abc import Iterator
from datetime import timedelta

import numpy

from django.db.models import QuerySet
from django.db.models.functions import Lower
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from radiofeed import iterators, tokenizer
from radiofeed.podcasts.models import Category, Podcast, Recommendation

logger = logging.getLogger(__name__)


def recommend() -> None:
    """Generates Recommendation instances based on podcast similarity, grouped by language and category.

    Any existing recommendations are first deleted.

    Only podcasts matching certain languages and updated within the past 90 days are included.
    """
    podcasts = (
        Podcast.objects.filter(
            pub_date__gt=timezone.now() - timedelta(days=90), active=True
        )
        .filter(language__in=tokenizer.NLTK_LANGUAGES)
        .exclude(extracted_text="")
    )

    categories = Category.objects.order_by("name")

    # separate by language, so we don't get false matches

    for language in podcasts.values_list(Lower("language"), flat=True).distinct():
        Recommender(language).recommend(podcasts, categories)


class Recommender:
    """Creates recommendations for given language, based around text content and common categories."""

    _num_matches: int = 12

    def __init__(self, language: str):
        self._language = language

        self._vectorizer = TfidfVectorizer(
            stop_words=list(tokenizer.get_stopwords(self._language)),
            max_features=None,
            ngram_range=(1, 2),
        )

    def recommend(
        self, podcasts: QuerySet[Podcast], categories: QuerySet[Category]
    ) -> None:
        """Creates recommendation instances."""
        # Delete existing recommendations first
        Recommendation.objects.filter(podcast__language=self._language).bulk_delete()

        logger.info("language:%s", self._language)
        for batch in iterators.batcher(
            self._build_matches_dict(podcasts, categories).items(), 100
        ):
            Recommendation.objects.bulk_create(
                (
                    Recommendation(
                        podcast_id=podcast_id,
                        recommended_id=recommended_id,
                        similarity=numpy.median(scores),
                        frequency=len(scores),
                    )
                    for (podcast_id, recommended_id), scores in batch
                ),
                ignore_conflicts=True,
            )

    def _build_matches_dict(
        self, podcasts: QuerySet[Podcast], categories: QuerySet[Category]
    ) -> collections.defaultdict[tuple[int, int], list[float]]:
        matches = collections.defaultdict(list)

        for category in categories:
            for (
                podcast_id,
                recommended_id,
                similarity,
            ) in self._match_podcasts_in_category(podcasts, category):
                matches[(podcast_id, recommended_id)].append(similarity)

        return matches

    def _match_podcasts_in_category(
        self, podcasts: QuerySet[Podcast], category: Category
    ) -> Iterator[tuple[int, int, float]]:
        # build a data model of podcasts with same language and category
        #
        logger.info("category:%s", category)

        rows = dict(
            podcasts.filter(
                language=self._language,
                categories=category,
            )
            .values_list("id", "extracted_text")
            .iterator()
        )

        if not rows:
            return  # pragma: no cover

        logger.info("building cosim...")

        try:
            cosine_sim = cosine_similarity(
                self._vectorizer.fit_transform(rows.values())
            )
        except ValueError:  # pragma: no cover
            return

        logger.info("cosim done")

        podcast_ids = list(rows.keys())

        for current_id, similar in zip(podcast_ids, cosine_sim):
            try:
                for recommended_id, similarity in self._find_similar_pairs(
                    current_id,
                    podcast_ids,
                    similar,
                ):
                    yield current_id, recommended_id, similarity

            except IndexError:  # pragma: no cover
                continue

    def _find_similar_pairs(
        self, current_id: int, podcast_ids: list[int], similar: list[float]
    ) -> Iterator[tuple[int, float]]:
        sorted_similar = sorted(
            enumerate(similar),
            key=operator.itemgetter(1),
            reverse=True,
        )[: self._num_matches]

        for index, similarity in sorted_similar:
            if similarity > 0 and (value := podcast_ids[index]) != current_id:
                yield value, round(similarity, 2)
