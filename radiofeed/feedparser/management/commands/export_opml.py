import argparse
import sys
from typing import IO

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """BaseCommand subclass"""

    help = "Generate OPML document from all public feeds"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command-line arguments"""
        parser.add_argument(
            "file",
            type=argparse.FileType("w"),
            default=sys.stdout,
        )
        parser.add_argument(
            "--promoted",
            action="store_true",
            default=False,
            help="Export only promoted podcasts",
        )

    def handle(self, **options) -> None:
        """Implementation of command."""
        writer: IO = options["file"]
        promoted: bool = options["promoted"]

        podcasts = Podcast.objects.published().filter(private=False).order_by("title")

        if promoted:
            podcasts = podcasts.filter(promoted=True)

        writer.write(
            render_to_string(
                "feedparser/podcasts.opml",
                {
                    "podcasts": podcasts,
                    "site": Site.objects.get_current(),
                },
            )
        )
