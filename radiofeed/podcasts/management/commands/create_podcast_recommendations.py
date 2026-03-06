from django.core.management import BaseCommand
from django.db.models.functions import Lower

from radiofeed.podcasts import recommender, tokenizer
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Django management command to create podcast recommendations for specified languages or all languages if none are specified."""

    help = "Create podcast recommendations for all languages."

    def handle(self, **options) -> None:
        """Commmand handler."""
        languages = (
            Podcast.objects.annotate(language_code=Lower("language"))
            .filter(language_code__in=tokenizer.get_language_codes())
            .values_list("language_code", flat=True)
            .order_by("language_code")
            .distinct()
        )

        for language in languages:
            recommender.recommend(language)
            self.stdout.write(f"Recommendations created for language: {language}")
