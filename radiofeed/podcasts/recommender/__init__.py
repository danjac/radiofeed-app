import collections
import datetime
import logging
import operator
import statistics

from typing import Dict, Generator, List, Tuple

import pandas

from django.db import transaction
from django.db.models import QuerySet
from django.db.models.functions import Lower
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..models import Category, Podcast, Recommendation
from .text_parser import get_stopwords

logger = logging.getLogger(__name__)

MatchesDict = Dict[Tuple[int, int], List[float]]

NUM_MATCHES: int = 12
NUM_RECENT_EPISODES: int = 6
MAX_PUB_DAYS: int = 90


def recommend() -> None:
    podcasts = get_podcast_queryset()

    # separate by language, so we don't get false matches
    categories = Category.objects.order_by("name")

    languages = [
        lang
        for lang in podcasts.values_list(Lower("language"), flat=True).distinct()
        if lang
    ]

    for language in languages:
        create_recommendations_for_language(podcasts, language, categories)


def get_podcast_queryset() -> QuerySet:
    min_pub_date = timezone.now() - datetime.timedelta(days=MAX_PUB_DAYS)
    return Podcast.objects.filter(pub_date__gt=min_pub_date).exclude(extracted_text="")


def create_recommendations_for_language(
    podcasts: QuerySet, language: str, categories: QuerySet
) -> None:
    logger.info("Recommendations for %s", language)

    matches = build_matches_dict(podcasts, language, categories)

    with transaction.atomic():

        Recommendation.objects.filter(podcast__language=language).delete()

        if matches:
            logger.info("Inserting %d recommendations:%s", len(matches), language)
            Recommendation.objects.bulk_create(
                recommendations_from_matches(matches),
                batch_size=100,
                ignore_conflicts=True,
            )


def build_matches_dict(
    podcasts: QuerySet, language: str, categories: QuerySet
) -> MatchesDict:

    matches = collections.defaultdict(list)
    podcasts = podcasts.filter(language__iexact=language)

    # individual graded category matches
    for category in categories:
        logger.info("Recommendations for %s:%s", language, category)
        for (podcast_id, recommended_id, similarity,) in find_similarities_for_podcasts(
            podcasts.filter(categories=category), language
        ):
            matches[(podcast_id, recommended_id)].append(similarity)

    return matches


def recommendations_from_matches(matches: MatchesDict) -> Generator:
    for (podcast_id, recommended_id), values in matches.items():
        frequency = len(values)
        similarity = statistics.median(values)

        yield Recommendation(
            podcast_id=podcast_id,
            recommended_id=recommended_id,
            similarity=similarity,
            frequency=frequency,
        )


def find_similarities_for_podcasts(podcasts: QuerySet, language: str) -> Generator:

    for podcast_id, recommended in find_similarities(podcasts, language):
        for recommended_id, similarity in recommended:
            similarity = round(similarity, 2)
            if similarity > 0:
                yield podcast_id, recommended_id, similarity


def find_similarities(podcasts: QuerySet, language: str) -> Generator:
    """Given a queryset, will yield tuples of
    (id, (similar_1, similar_2, ...)) based on text content.
    """
    if not podcasts.exists():
        return

    df = pandas.DataFrame(podcasts.values("id", "extracted_text"))

    df.drop_duplicates(inplace=True)

    vec = TfidfVectorizer(
        stop_words=get_stopwords(language),
        max_features=3000,
        ngram_range=(1, 2),
    )

    try:
        count_matrix = vec.fit_transform(df["extracted_text"])
    except ValueError:
        # empty set
        return

    cosine_sim = cosine_similarity(count_matrix)

    for index in df.index:
        current_id = df.loc[index, "id"]
        try:
            similar = list(enumerate(cosine_sim[index]))
        except IndexError:
            continue
        sorted_similar = sorted(similar, key=operator.itemgetter(1), reverse=True)[
            :NUM_MATCHES
        ]
        matches = [
            (df.loc[row, "id"], similarity)
            for row, similarity in sorted_similar
            if df.loc[row, "id"] != current_id
        ]
        yield (current_id, matches)
