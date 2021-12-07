from __future__ import annotations

import argparse

from django.core.management.base import BaseCommand

from jcasts.websub import subscriber


class Command(BaseCommand):
    help = "Create or renew subscriptions"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--limit",
            help="Max limit of feeds",
            type=int,
            default=200,
        )

    def handle(self, *args, **options) -> None:
        subscriber.enqueue(options["limit"])
