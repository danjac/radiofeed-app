from django.core.management.base import BaseCommand
from django.db.models.functions import Lower

from listenwave.podcasts import recommender, tokenizer
from listenwave.podcasts.models import Podcast
from listenwave.thread_pool import db_threadsafe, thread_pool_map


class Command(BaseCommand):
    """Create podcast recommendations command"""

    help = "Create podcast recommendations"

    def handle(self, **options):
        """Create recommendations for all podcasts"""

        @db_threadsafe
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

        for language in thread_pool_map(_worker, languages):
            self.stdout.write(f"Recommendations created for language: {language}")
