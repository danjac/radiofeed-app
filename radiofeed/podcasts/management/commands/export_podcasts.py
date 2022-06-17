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
        with (stream := options["output"]):
            writer = csv.writer(stream)
            for rss in Podcast.objects.values_list("rss", flat=True):
                writer.writerow([rss])
