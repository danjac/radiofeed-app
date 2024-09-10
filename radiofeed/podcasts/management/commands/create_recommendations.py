from django.core.management.base import BaseCommand

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor


class Command(BaseCommand):
    """Base implementation."""

    def handle(self, *args, **options) -> None:
        """Implementation of command."""
        with DatabaseSafeThreadPoolExecutor() as executor:
            executor.db_safe_map(
                lambda language: recommender.recommend(language),
                tokenizer.NLTK_LANGUAGES,
            )
