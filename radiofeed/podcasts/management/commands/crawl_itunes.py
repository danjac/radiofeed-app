from django.core.management.base import BaseCommand

from radiofeed.podcasts import itunes


class Command(BaseCommand):
    help = """
    Crawls iTunes for new podcasts.
    """

    def handle(self, *args, **kwargs):
        for feed in itunes.crawl():
            if feed.podcast:
                self.stdout.write(feed.title)
            else:
                self.stdout.write(self.style.SUCCESS(feed.title))
