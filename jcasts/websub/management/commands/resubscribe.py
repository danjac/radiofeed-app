from __future__ import annotations

import argparse

from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.websub import subscriber


class Command(BaseCommand):
    help = "Create or renew subscriptions"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--since",
            help="Minutes since original request",
            type=int,
            default=30,
        )

    def handle(self, *args, **options) -> None:
        subscriber.resubscribe(timedelta(minutes=options["since"]))
