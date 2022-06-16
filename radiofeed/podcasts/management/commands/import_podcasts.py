from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    help = """
    Import podcast feeds from text file
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("filename", help="Path to file")

    def handle(self, filename: str, *args, **options):
        podcasts = Podcast.objects.bulk_create(
            [
                Podcast(rss=feed)
                for feed in filter(
                    None, map(str.strip, open(filename).read().splitlines())
                )
            ],
            ignore_conflicts=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f"{len(podcasts)} podcasts added to the database")
        )
