from django.core.management.base import BaseCommand

from radiofeed.podcasts import itunes


class Command(BaseCommand):
    help = """
    Crawls iTunes for new podcasts.
    """

    def handle(self, *args, **options):
        for feed in itunes.crawl():
            style = self.style.SUCCESS if feed.podcast is None else self.style.NOTICE
            self.stdout.write(style(feed.title))
