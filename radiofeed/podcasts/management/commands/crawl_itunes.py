from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.podcasts import itunes


class Command(BaseCommand):
    help = """
    Crawls iTunes for new podcasts.
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--url", help="iTunes web page", default=None)

    def handle(self, url: str | None = None, *args, **options):
        for counter, feed in enumerate(
            itunes.parse_genre(url) if url else itunes.crawl()
        ):

            message = f"{counter}: {feed.title}"

            if feed.podcast:
                self.stdout.write(message)
            else:
                self.stdout.write(self.style.SUCCESS(message))
