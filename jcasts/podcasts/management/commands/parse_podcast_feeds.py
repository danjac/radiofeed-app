from __future__ import annotations

import argparse

from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Parse podcast feeds"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--frequency", help="Frequency between updates (minutes)", default=60
        )

    def handle(self, *args, **options) -> None:
        feed_parser.parse_podcast_feeds(timedelta(minutes=options["frequency"]))
