import pathlib
from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.opml import parse_opml


class Command(BaseCommand):
    """Django management command."""

    help = """Create new podcast feeds from OPML document."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument("filename", help="OPML file")

    def handle(self, filename: str, **options):
        """Handle implementation."""
        with pathlib.Path(filename).open("rb") as fp:
            podcasts = Podcast.objects.bulk_create(
                [Podcast(rss=rss) for rss in parse_opml(fp)],
                ignore_conflicts=True,
            )

        if num_podcasts := len(podcasts):
            self.stdout.write(self.style.SUCCESS(f"{num_podcasts} podcasts imported"))
        else:
            self.stdout.write("No podcasts found")
