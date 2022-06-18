from django.core.management.base import BaseCommand

from radiofeed.podcasts import itunes
from radiofeed.podcasts.tasks import parse_itunes_feed


class Command(BaseCommand):
    help = """
    Crawls iTunes for new podcasts.
    """

    def handle(self, *args, **options):
        parse_itunes_feed.map(itunes.crawl())
