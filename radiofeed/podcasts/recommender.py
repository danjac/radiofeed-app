from __future__ import annotations

import collections
import operator

from datetime import timedelta
from typing import Iterator

import numpy
import pandas

from django.db.models import QuerySet
from django.db.models.functions import Lower
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from radiofeed.common import batcher, tokenizer
from radiofeed.podcasts.models import Category, Podcast, Recommendation


def recommend() -> None:
    """Generates Recommendation instances based on podcast similarity, grouped by language and category.

    Any existing recommendations are first deleted.

    Only podcasts matching certain languages and updated within the past 90 days are included.
    """
    podcasts = (
        Podcast.objects.filter(pub_date__gt=timezone.now() - timedelta(days=90))
        .filter(language__in=tokenizer.NLTK_LANGUAGES)
        .exclude(extracted_text="")
    )

    Recommendation.objects.bulk_delete()

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
            stop_words=tokenizer.get_stopwords(self._language),
            max_features=3000,
            ngram_range=(1, 2),
        )

    def recommend(
        self, podcasts: QuerySet[Podcast], categories: QuerySet[Category]
    ) -> None:
        """Creates recommendation instances."""
        for batch in batcher.batcher(
            self._build_matches_dict(podcasts, categories).items(), 1000
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

        df = pandas.DataFrame(
            podcasts.filter(
                language=self._language,
                categories=category,
            )
            .values("id", "extracted_text")
            .distinct()
        )

        if df.empty:
            return  # pragma: no cover

        df.drop_duplicates(inplace=True)

        try:
            cosine_sim = cosine_similarity(
                self._vectorizer.fit_transform(df["extracted_text"])
            )
        except ValueError:  # pragma: no cover
            return

        # find matching similar pairs
        #
        for index in df.index:
            try:
                podcast_id, recommended = self._find_similar_pairs(
                    df,
                    similar=cosine_sim[index],
                    current_id=df.loc[index, "id"],
                )

                for recommended_id, similarity in recommended:
                    if similarity > 0:
                        yield podcast_id, recommended_id, similarity

            except IndexError:  # pragma: no cover
                continue

    def _find_similar_pairs(
        self, df: pandas.DataFrame, similar: list[float], current_id: int
    ) -> tuple[int, Iterator[tuple[int, float]]]:

        sorted_similar = sorted(
            enumerate(similar),
            key=operator.itemgetter(1),
            reverse=True,
        )[: self._num_matches]

        return (
            current_id,
            (
                (df.loc[row, "id"], round(similarity, 2))
                for row, similarity in sorted_similar
                if df.loc[row, "id"] != current_id
            ),
        )
