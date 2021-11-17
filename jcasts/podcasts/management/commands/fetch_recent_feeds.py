from __future__ import annotations

import argparse

from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import podcastindex


class Command(BaseCommand):
    help = "Fetch recent podcast feeds from Podcastindex.org"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--frequency",
            help="Frequency between updates (minutes)",
            type=int,
            default=60,
        )

        parser.add_argument(
            "--limit",
            help="Max count",
            type=int,
            default=100,
        )

    def handle(self, *args, **options) -> None:
        num_podcasts = podcastindex.fetch_recent_feeds(
            frequency=timedelta(minutes=options["frequency"]), limit=options["limit"]
        )
        self.stdout.write(
            self.style.SUCCESS(f"{num_podcasts} podcast feeds queued for update")
        )
