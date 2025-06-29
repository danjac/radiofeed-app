from django.core.management.base import BaseCommand
from django.db.models.functions import Lower

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Create recommendations for all podcasts in the database."""

    def handle(self, **options) -> None:
        """Create recommendations for all podcasts"""
        languages = (
            Podcast.objects.annotate(language_code=Lower("language"))
            .filter(language_code__in=tokenizer.get_language_codes())
            .values_list("language_code", flat=True)
            .order_by("language_code")
            .distinct()
        )

        for language in languages:
            """Create recommendations for a specific language."""
            recommender.recommend(language)
            self.stdout.write(
                self.style.SUCCESS(f"Recommendations created for language: {language}")
            )
