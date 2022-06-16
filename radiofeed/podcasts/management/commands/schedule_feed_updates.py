from __future__ import annotations

from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.podcasts import feed_scheduler


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--limit", help="Limit", type=int, default=360)

    def handle(self, *args, **options) -> None:
        feed_scheduler.schedule(options["limit"])
