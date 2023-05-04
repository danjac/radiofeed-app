from django.core.management.base import BaseCommand

from radiofeed.podcasts import itunes


class Command(BaseCommand):
    """Django management command."""

    help = """Crawls iTunes for new podcasts."""

    def handle(self, **options):
        """Handle implementation."""
        for feed in itunes.crawl():
            style = self.style.SUCCESS if feed.podcast is None else self.style.NOTICE
            self.stdout.write(style(feed.title))
