from django.core.management.base import BaseCommand
from django.db.models.functions import Lower

from listenwave import tokenizer
from listenwave.podcasts import recommender
from listenwave.podcasts.models import Podcast
from listenwave.thread_pool import map_thread_pool


class Command(BaseCommand):
    """Create podcast recommendations command"""

    help = "Create podcast recommendations"

    def handle(self, **options):
        """Create recommendations for all podcasts"""

        def _worker(language: str) -> str:
            recommender.recommend(language)
            return language

        languages = (
            Podcast.objects.annotate(language_code=Lower("language"))
            .filter(language_code__in=tokenizer.get_language_codes())
            .values_list("language_code", flat=True)
            .order_by("language_code")
            .distinct()
        )

        for language in map_thread_pool(_worker, languages):
            self.stdout.write(f"Recommendations created for language: {language}")
