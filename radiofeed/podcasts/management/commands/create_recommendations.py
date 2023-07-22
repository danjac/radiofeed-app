from django.core.management.base import BaseCommand

from radiofeed import tokenizer
from radiofeed.futures import DatabaseSafeThreadPoolExecutor
from radiofeed.podcasts import recommender


class Command(BaseCommand):
    """Django command."""

    help = """Runs recommendation algorithms."""

    def handle(self, **options):
        """Command handler implementation."""
        with DatabaseSafeThreadPoolExecutor() as executor:
            executor.db_safe_map(self._recommend, tokenizer.NLTK_LANGUAGES)

    def _recommend(self, language: str):
        self.stdout.write(f"Creating recommendations for language: {language}...")
        recommender.recommend(language)
        self.stdout.write(
            self.style.SUCCESS(f"Recommendations created for language: {language}")
        )
