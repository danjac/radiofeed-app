import argparse

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandParser
from django.template.loader import render_to_string

from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Django management command to export all podcasts to an OPML file."""

    help = "Export all podcasts to an OPML file."

    def add_arguments(self, parser: CommandParser) -> None:
        """Parse command line arguments."""

        parser.add_argument(
            "file",
            type=argparse.FileType("w"),
            help="OPML file to write",
        )

        parser.add_argument(
            "--promoted",
            action="store_true",
            help="Export only promoted podcasts",
        )

    def handle(self, **options) -> None:
        """Exports all podcasts to an OPML file."""
        podcasts = Podcast.objects.published().filter(private=False).order_by("title")

        if options["promoted"]:
            podcasts = podcasts.filter(promoted=True)

        options["file"].write(
            render_to_string(
                "feedparser/podcasts.opml",
                {
                    "podcasts": podcasts,
                    "site": Site.objects.get_current(),
                },
            )
        )
