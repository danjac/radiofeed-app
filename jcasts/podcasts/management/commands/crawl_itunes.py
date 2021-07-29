from django.core.management.base import BaseCommand

from jcasts.podcasts import itunes


class Command(BaseCommand):
    help = "Crawl iTunes for new podcasts"

    def handle(self, *args, **options) -> None:
        itunes.crawl_itunes()
