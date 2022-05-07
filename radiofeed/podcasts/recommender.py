from __future__ import annotations

import collections
import logging
import operator
import statistics

from datetime import timedelta
from typing import Generator

import pandas

from django.db.models import QuerySet
from django.db.models.functions import Lower
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from radiofeed.podcasts.models import Category, Podcast, Recommendation
from radiofeed.podcasts.parsers.text_parser import get_stopwords

logger = logging.getLogger(__name__)


Similarities = tuple[int, list[tuple[int, float]]]


def recommend(since: timedelta = timedelta(days=90), num_matches: int = 12) -> None:

    podcasts = Podcast.objects.filter(pub_date__gt=timezone.now() - since).exclude(
        extracted_text="",
        language="",
    )

    Recommendation.objects.bulk_delete()

    categories = Category.objects.order_by("name")

    # separate by language, so we don't get false matches
    for language in podcasts.values_list(Lower("language"), flat=True).distinct():
        Recommender(language, num_matches).recommend(podcasts, categories)


class Recommender:
    def __init__(self, language: str, num_matches: int):
        self.language = language
        self.num_matches = num_matches

    def recommend(
        self, podcasts: QuerySet, categories: QuerySet
    ) -> list[Recommendation]:

        if matches := self.build_matches_dict(podcasts, categories):

            logger.info("Inserting %d recommendations:%s", len(matches), self.language)

            return Recommendation.objects.bulk_create(
                self.recommendations_from_matches(matches),
                batch_size=100,
                ignore_conflicts=True,
            )

        return []

    def build_matches_dict(
        self,
        podcasts: QuerySet,
        categories: QuerySet,
    ) -> dict[tuple[int, int], list[float]]:

        matches = collections.defaultdict(list)
        podcasts = podcasts.filter(language__iexact=self.language)

        # individual graded category matches
        for category in categories:
            logger.info("Recommendations for %s:%s", self.language, category)
            for (
                podcast_id,
                recommended_id,
                similarity,
            ) in self.find_similarities_for_podcasts(
                podcasts.filter(categories=category)
            ):
                matches[(podcast_id, recommended_id)].append(similarity)

        return matches

    def recommendations_from_matches(
        self, matches: dict[tuple[int, int], list[float]]
    ) -> Generator[Recommendation, None, None]:
        for (podcast_id, recommended_id), values in matches.items():
            yield Recommendation(
                podcast_id=podcast_id,
                recommended_id=recommended_id,
                similarity=statistics.median(values),
                frequency=len(values),
            )

    def find_similarities_for_podcasts(
        self,
        podcasts: QuerySet,
    ) -> Generator[tuple[int, int, float], None, None]:

        if not podcasts.exists():  # pragma: no cover
            return

        for podcast_id, recommended in self.find_similarities(podcasts):
            for recommended_id, similarity in recommended:
                similarity = round(similarity, 2)
                if similarity > 0:
                    yield podcast_id, recommended_id, similarity

    def find_similarities(
        self, podcasts: QuerySet
    ) -> Generator[Similarities, None, None]:
        """Given a queryset, will yield tuples of
        (id, (similar_1, similar_2, ...)) based on text content.
        """

        df = pandas.DataFrame(podcasts.values("id", "extracted_text"))

        df.drop_duplicates(inplace=True)

        vec = TfidfVectorizer(
            stop_words=get_stopwords(self.language),
            max_features=3000,
            ngram_range=(1, 2),
        )

        try:
            count_matrix = vec.fit_transform(df["extracted_text"])
        except ValueError:  # pragma: no cover
            return

        cosine_sim = cosine_similarity(count_matrix)

        for index in df.index:
            try:
                yield self.find_similarity(
                    df,
                    similar=cosine_sim[index],
                    current_id=df.loc[index, "id"],
                )
            except IndexError:  # pragma: no cover
                pass

    def find_similarity(
        self,
        df: pandas.DataFrame,
        similar: list[float],
        current_id: int,
    ) -> Similarities:

        sorted_similar = sorted(
            list(enumerate(similar)),
            key=operator.itemgetter(1),
            reverse=True,
        )[: self.num_matches]

        matches = [
            (df.loc[row, "id"], similarity)
            for row, similarity in sorted_similar
            if df.loc[row, "id"] != current_id
        ]
        return (current_id, matches)
