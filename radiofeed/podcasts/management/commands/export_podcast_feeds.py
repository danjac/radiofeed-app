import csv

from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    help = """
    Export podcast feed URLs to text file
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("filename", help="Path to file")

    def handle(self, filename: str, *args, **kwargs) -> None:

        counter: int = 0

        with open(filename, "w") as fp:
            writer = csv.writer(fp)
            for counter, rss in enumerate(
                Podcast.objects.values_list("rss", flat=True), 1
            ):
                writer.writerow([rss])

        self.stdout.write(
            self.style.SUCCESS(f"{counter} podcasts written to {filename}")
        )
