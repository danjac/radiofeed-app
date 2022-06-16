import csv

from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    help = """
    Export podcast feed URLs to text file
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("-o", "--output", help="Path to file")

    def handle(self, *args, **options) -> None:

        counter: int = 0

        if filename := options.get("output"):
            stream = open(filename, "w")
        else:
            stream = self.stdout

        with stream:
            writer = csv.writer(stream)
            for counter, rss in enumerate(
                Podcast.objects.values_list("rss", flat=True), 1
            ):
                writer.writerow([rss])
