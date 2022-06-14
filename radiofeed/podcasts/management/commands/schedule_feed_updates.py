from __future__ import annotations

import multiprocessing

from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.podcasts import feed_scheduler


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--limit", help="Limit (per CPU)", type=int, default=100)
        parser.add_argument("--timeout", help="Timeout(seconds)", type=int, default=360)

    def handle(self, *args, **kwargs) -> None:

        # parse podcasts up to CPU-based limit
        # example: if 3xCPU and --limit=100, then parse 300 each time

        podcast_ids = feed_scheduler.enqueue_scheduled_feeds(
            round(multiprocessing.cpu_count() * kwargs["limit"]),
            job_timeout=kwargs["timeout"],
        )

        self.stdout.write(f"{len(podcast_ids)} podcasts queued for update")
