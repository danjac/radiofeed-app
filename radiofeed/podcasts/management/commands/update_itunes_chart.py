from django.core.management.base import BaseCommand

from radiofeed.http_client import get_client
from radiofeed.podcasts.itunes import update_chart


class Command(BaseCommand):
    """Django command to crawl iTunes Top Chart."""

    help = "Update podcasts from iTunes Top Chart"

    def handle(self, *args, **options):
        """Updated iTunes Top Chart."""
        for ranking, feed in enumerate(update_chart(get_client()), 1):
            self.stdout.write(self.style.SUCCESS(f"{ranking}: {feed.title}"))
