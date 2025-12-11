from django.core.management.base import BaseCommand
from django.db.models.functions import Lower

from listenwave import tokenizer
from listenwave.podcasts import recommender
from listenwave.podcasts.models import Podcast


class Command(BaseCommand):
    """Create podcast recommendations command"""

    help = "Create podcast recommendations"

    def handle(self, **options):
        """Create recommendations for all podcasts"""
        languages = (
            Podcast.objects.annotate(language_code=Lower("language"))
            .filter(language_code__in=tokenizer.get_language_codes())
            .values_list("language_code", flat=True)
            .order_by("language_code")
            .distinct()
        )

        for language in languages:
            self.stdout.write(f"Recommendations created for language: {language}")
            recommender.recommend(language)
