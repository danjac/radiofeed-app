from django.core.management.base import BaseCommand
from django.db.models import ValuesQuerySet
from django.db.models.functions import Lower

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool


class Command(BaseCommand):
    """Command implementation."""

    help = "Create recommendations for all podcasts"

    def handle(self, **options) -> None:
        """Handle implementation."""
        execute_thread_pool(self._create_recommendations, self._get_languages())

    def _create_recommendations(self, language: str) -> None:
        recommender.recommend(language)
        self.stdout.write(
            self.style.SUCCESS(
                f"Recommendations created for language: {language}",
            ),
        )

    def _get_languages(self) -> ValuesQuerySet:
        return (
            Podcast.objects.annotate(language_code=Lower("language"))
            .filter(language_code__in=tokenizer.get_language_codes())
            .values_list("language_code", flat=True)
            .order_by("language_code")
            .distinct()
        )
