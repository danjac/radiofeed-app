import csv
import sys

from argparse import ArgumentParser, FileType

from django.core.management.base import BaseCommand

from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    help = """
    Export podcast feed URLs to text file
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("output", nargs="?", type=FileType("w"), default=sys.stdout)

    def handle(self, *args, **options) -> None:

        counter: int = 0

        with (stream := options["output"]):
            writer = csv.writer(stream)
            for counter, rss in enumerate(
                Podcast.objects.values_list("rss", flat=True), 1
            ):
                writer.writerow([rss])
