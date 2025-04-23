from django.core.management.base import BaseCommand

from radiofeed import tokenizer
from radiofeed.podcasts import recommender


class Command(BaseCommand):
    """Command implementation"""

    help = "Generate podcast recommendations"

    def handle(self, **options) -> None:
        """Command implementation"""

        for language in tokenizer.LANGUAGES:
            recommender.recommend(language)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Recommendations created for language: {language}",
                )
            )
