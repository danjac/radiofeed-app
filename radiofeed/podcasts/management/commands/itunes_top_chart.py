from django.core.management.base import BaseCommand

from radiofeed.http_client import get_client
from radiofeed.podcasts.itunes import top_chart


class Command(BaseCommand):
    """Django command to crawl iTunes Top Chart."""

    help = "Crawl iTunes Top Chart"

    def handle(self, *args, **options):
        """Crawl iTunes Top Chart."""
        if podcasts := top_chart(get_client()):
            self.stdout.write(self.style.SUCCESS(f"Found {len(podcasts)} podcasts"))
