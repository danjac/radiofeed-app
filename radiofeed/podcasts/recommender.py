import collections
import logging
import operator

from datetime import timedelta
from typing import Generator

import numpy
import pandas

from django.db.models import QuerySet
from django.db.models.functions import Lower
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from radiofeed.common.utils.iterators import batcher
from radiofeed.common.utils.text import NLTK_LANGUAGES, get_stopwords
from radiofeed.podcasts.models import Category, Podcast, Recommendation

DEFAULT_TIME_PERIOD = timedelta(days=90)


def recommend(since: timedelta = DEFAULT_TIME_PERIOD, num_matches: int = 12) -> None:
    """Generates Recommendation instances based on podcast similarity, grouped by language.

    Any existing recommendations are first deleted.

    Args:
        since: include podcasts last published since this period.
        num_matches: total number of recommendations to create for each podcast

    """
    podcasts = (
        Podcast.objects.filter(pub_date__gt=timezone.now() - since)
        .filter(language__in=NLTK_LANGUAGES)
        .exclude(extracted_text="")
    )

    logging.info("Deleting existing recommendations...")

    Recommendation.objects.bulk_delete()

    categories = Category.objects.order_by("name")

    # separate by language, so we don't get false matches

    for language in podcasts.values_list(Lower("language"), flat=True).distinct():
        Recommender(language, num_matches).recommend(podcasts, categories)


class Recommender:
    """Creates recommendations for given language, based around text content and common categories.

    Args:
        language: two-character language code e.g. "en"
        num_matches: number of recommendations to create
    """

    _batch_size = 1000

    def __init__(self, language: str, num_matches: int):

        self._language = language
        self._num_matches = num_matches

        self._vectorizer = TfidfVectorizer(
            stop_words=get_stopwords(self._language),
            max_features=3000,
            ngram_range=(1, 2),
        )

    def recommend(self, podcasts: QuerySet[Podcast], categories: QuerySet[Category]) -> None:
        """Creates recommendation instances.

        Args:
            podcasts: podcast instances
            categories: category instances
        """
        logging.info("Building matches for language [%s]...", self._language)

        podcasts = podcasts.filter(language=self._language)
        matches = collections.defaultdict(list)

        for category in categories:

            for podcast_id, recommended_id, similarity in self._find_similarities(category, podcasts):
                matches[(podcast_id, recommended_id)].append(similarity)

        num_matches = len(matches)

        logging.info("Matches for language [%s]: %d", self._language, num_matches)

        for counter, batch in enumerate(batcher(matches.items(), self._batch_size)):

            logging.info(
                "Saving batch for language [%s]: %d-%d / %d",
                self._language,
                counter * self._batch_size,
                (counter * self._batch_size) + self._batch_size,
                num_matches,
            )

            Recommendation.objects.bulk_create(
                (
                    Recommendation(
                        podcast_id=podcast_id,
                        recommended_id=recommended_id,
                        similarity=numpy.median(values),
                        frequency=len(values),
                    )
                    for (podcast_id, recommended_id), values in batch
                ),
                ignore_conflicts=True,
            )

    def _find_similarities(
        self, category: Category, podcasts: QuerySet[Podcast]
    ) -> Generator[tuple[int, int, float], None, None]:
        logging.info("Building matches for category [%s] [%s]", self._language, category.name)

        df = pandas.DataFrame(podcasts.filter(categories=category).values("id", "extracted_text").distinct())

        if df.empty:
            return  # pragma: no cover

        df.drop_duplicates(inplace=True)

        try:
            cosine_sim = cosine_similarity(self._vectorizer.fit_transform(df["extracted_text"]))
        except ValueError:  # pragma: no cover
            return

        for index in df.index:
            try:
                podcast_id, recommended = self._find_similarity(
                    df,
                    similar=cosine_sim[index],
                    current_id=df.loc[index, "id"],
                )

                for recommended_id, similarity in recommended:
                    if (similarity := round(similarity, 2)) > 0:
                        yield podcast_id, recommended_id, similarity

            except IndexError:  # pragma: no cover
                continue

    def _find_similarity(
        self, df: pandas.DataFrame, similar: list[float], current_id: int
    ) -> tuple[int, Generator[tuple[int, float], None, None]]:

        sorted_similar = sorted(
            enumerate(similar),
            key=operator.itemgetter(1),
            reverse=True,
        )[: self._num_matches]

        return (
            current_id,
            ((df.loc[row, "id"], similarity) for row, similarity in sorted_similar if df.loc[row, "id"] != current_id),
        )
