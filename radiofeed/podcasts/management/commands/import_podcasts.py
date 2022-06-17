import sys

from argparse import ArgumentParser, FileType

from django.core.management.base import BaseCommand

from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    help = """
    Import podcast feeds from text file
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("input", nargs="?", type=FileType("r"), default=sys.stdin)

    def handle(self, *args, **options):
        podcasts = Podcast.objects.bulk_create(
            [
                Podcast(rss=feed)
                for feed in filter(
                    None, map(str.strip, options["input"].read().splitlines())
                )
            ],
            ignore_conflicts=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f"{len(podcasts)} podcasts added to the database")
        )
