from django.db.models import QuerySet
from django.db.models.functions import Lower
from django_typer.management import TyperCommand

from radiofeed.podcasts import recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool


class Command(TyperCommand):
    """Generates podcast recommendations based on similarity."""

    def handle(self) -> None:
        """Generate podcast recommendations"""
        execute_thread_pool(self._create_recommendations, self._get_languages())

    def _create_recommendations(self, language: str) -> None:
        """Create recommendations for a specific language"""
        recommender.recommend(language)
        self.stdout.write(
            self.style.SUCCESS(
                f"Recommendations created for language: {language}",
            )
        )

    def _get_languages(self) -> QuerySet:
        return (
            Podcast.objects.annotate(language_code=Lower("language"))
            .values_list(
                "language_code",
                flat=True,
            )
            .distinct()
        )
