# Standard Library
import collections
import datetime
import logging
import operator
import statistics

# Django
from django.contrib.postgres.aggregates import StringAgg
from django.db import transaction
from django.db.models import OuterRef, Q, Subquery
from django.db.models.functions import Lower
from django.utils import timezone

# Third Party Libraries
import pandas
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# RadioFeed
from radiofeed.episodes.models import Episode

# Local
from ..models import Category, Podcast, Recommendation
from .text_parser import extract_keywords, get_stopwords

logger = logging.getLogger(__name__)


class PodcastRecommender:
    def __init__(self, num_matches=12, num_recent_episodes=6, max_pub_days=90):
        self.num_matches = num_matches
        self.num_recent_episodes = num_recent_episodes
        self.max_pub_days = max_pub_days

    @classmethod
    def recommend(cls, *args, **kwargs):
        return cls(*args, **kwargs).do_recommend()

    def do_recommend(self):

        self.queryset = self.get_podcast_queryset()

        # separate by language, so we don't get false matches
        self.categories = Category.objects.order_by("name")

        languages = [
            lang
            for lang in self.queryset.values_list(
                Lower("language"), flat=True
            ).distinct()
            if lang
        ]

        for language in languages:
            self.create_recommendations_for_language(language)

    def get_podcast_queryset(self):
        min_pub_date = timezone.now() - datetime.timedelta(days=self.max_pub_days)

        return Podcast.objects.filter(pub_date__gt=min_pub_date).annotate(
            category_names=StringAgg(
                "categories__name",
                delimiter=" | ",
                ordering="categories__name",
                distinct=True,
            ),
            episode_titles=StringAgg(
                "episode__title",
                delimiter=" ",
                distinct=True,
                filter=Q(
                    episode__pk__in=Subquery(
                        Episode.objects.filter(
                            podcast=OuterRef("pk"), pub_date__gt=min_pub_date
                        )
                        .order_by("-pub_date")
                        .distinct()
                        .values("pk")[: self.num_recent_episodes]
                    )
                ),
            ),
        )

    def create_recommendations_for_language(self, language):
        logger.info("Recommendations for %s", language)

        matches = self.build_matches_dict(language)

        with transaction.atomic():

            Recommendation.objects.filter(podcast__language=language).delete()

            if matches:
                logger.info("Inserting %d recommendations:%s", len(matches), language)
                Recommendation.objects.bulk_create(
                    self.recommendations_from_matches(matches.items()),
                    batch_size=100,
                    ignore_conflicts=True,
                )

    def recommendations_from_matches(self, matches):
        for (podcast_id, recommended_id), values in matches:
            frequency = len(values)
            similarity = statistics.median(values)

            yield Recommendation(
                podcast_id=podcast_id,
                recommended_id=recommended_id,
                similarity=similarity,
                frequency=frequency,
            )

    def build_matches_dict(self, language):

        # dict of (podcast_id, recommended_id): similarity
        matches = collections.defaultdict(list)
        queryset = self.queryset.filter(language__iexact=language)

        # individual graded category matches
        for category in self.categories:
            logger.info("Recommendations for %s:%s", language, category)
            for (
                podcast_id,
                recommended_id,
                similarity,
            ) in self.find_similarities_for_podcasts(
                language, queryset.filter(categories=category)
            ):
                matches[(podcast_id, recommended_id)].append(similarity)

        return matches

    def find_similarities_for_podcasts(self, language, queryset):

        for podcast_id, recommended in self.find_similarities(
            language,
            queryset,
            fieldnames=[
                "title",
                "description",
                "keywords",
                "authors",
                "category_names",
                "episode_titles",
            ],
        ):
            for recommended_id, similarity in recommended:
                similarity = round(similarity, 2)
                if similarity > 0:
                    yield podcast_id, recommended_id, similarity

    def find_similarities(self, language, queryset, fieldnames):
        """Given a queryset, will yield tuples of
        (id, (similar_1, similar_2, ...)) based on text content.
        """
        if not queryset.exists():
            return

        df = pandas.DataFrame(queryset.values(*["id"] + list(fieldnames)))

        def combine(row):
            text = " ".join(row[col] for col in fieldnames if row[col])
            return " ".join([kw for kw in extract_keywords(language, text)])

        df["combined"] = df.apply(combine, axis=1)

        # remove any unused cols
        df.drop(fieldnames, axis=1)
        df.drop_duplicates(inplace=True)

        vec = TfidfVectorizer(
            stop_words=get_stopwords(language), max_features=3000, ngram_range=(1, 2),
        )

        try:
            count_matrix = vec.fit_transform(df["combined"])
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
                : self.num_matches
            ]
            matches = [
                (df.loc[row, "id"], similarity)
                for row, similarity in sorted_similar
                if df.loc[row, "id"] != current_id
            ]
            yield (current_id, matches)
