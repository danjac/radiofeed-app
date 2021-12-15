from __future__ import annotations

import argparse

from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = """
    Clears any podcasts stuck in the queue. This sometimes happens e.g. when
    restarting workers in a deployment.
    """

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "queues",
            help="Job queue",
            nargs="*",
            type=str,
        )

        parser.add_argument(
            "--all",
            help="Empty all queues",
            action="store_true",
            default=False,
        )

    def handle(self, queues: list[str], *args, **options) -> None:
        if options["all"]:
            count = feed_parser.empty_all_queues()
            self.stdout.write(f"{count} podcasts removed from all queues")
            return

        for queue in queues:
            count = feed_parser.empty_queue(queue)
            self.stdout.write(f"{count} podcasts removed from queue {queue}")
