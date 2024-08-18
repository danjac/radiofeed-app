from django.core.management.base import BaseCommand
from loguru import logger

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor


class Command(BaseCommand):
    """Base implementation."""

    def handle(self, *args, **options) -> None:
        """Implementation of command."""
        verbosity: int | None = options["verbosity"]
        if verbosity and verbosity > 1:
            logger.enable("radiofeed.podcasts.recommender")

        with DatabaseSafeThreadPoolExecutor() as executor:
            executor.db_safe_map(
                lambda language: recommender.recommend(language),
                tokenizer.NLTK_LANGUAGES,
            )
