from django.core.management.base import BaseCommand

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.thread_pool import execute_thread_pool


class Command(BaseCommand):
    """Django management command."""

    help = """Generate recommendations based on podcast similarity."""

    def handle(self, *args, **options):
        """Handle implementation."""
        execute_thread_pool(recommender.recommend, tokenizer.NLTK_LANGUAGES)
