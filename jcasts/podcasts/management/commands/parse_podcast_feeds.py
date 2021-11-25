from __future__ import annotations

import argparse

from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Parse podcast feeds"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--frequency",
            help="Frequency between updates (minutes)",
            type=int,
            default=60,
        )

        parser.add_argument(
            "--sporadic",
            help="Parse sporadic feeds",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options) -> None:
        frequency = timedelta(minutes=options["frequency"])

        num_podcasts = (
            feed_parser.parse_sporadic_feeds(frequency)
            if options["sporadic"]
            else feed_parser.parse_scheduled_feeds(frequency)
        )

        self.stdout.write(
            self.style.SUCCESS(f"{num_podcasts} podcast feeds queued for update")
        )
