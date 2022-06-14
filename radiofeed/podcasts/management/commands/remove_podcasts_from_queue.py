from __future__ import annotations

from argparse import ArgumentParser
from datetime import timedelta

from django.core.management.base import BaseCommand

from radiofeed.podcasts import feed_scheduler


class Command(BaseCommand):
    help = """
    Remove podcasts from feed update queue
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--timeout", help="Timeout(hours)", type=int, default=1)

    def handle(self, *args, **kwargs) -> None:
        num_podcasts = feed_scheduler.remove_feeds_from_queue(
            timedelta(hours=kwargs["timeout"])
        )
        self.stdout.write(f"{num_podcasts} podcasts removed from queue")
