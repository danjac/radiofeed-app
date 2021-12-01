from __future__ import annotations

import argparse
import logging

from django.core.management.base import BaseCommand, CommandError

from jcasts.podcasts import podping


class Command(BaseCommand):
    help = "Calls podping blockchain to get latest updates"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--from-minutes-ago",
            type=int,
            default=15,
        )

        parser.add_argument(
            "--keep-alive",
            action="store_true",
            default=False,
            help="Restart on error",
        )

    def handle(self, *args, **options) -> None:  # pragma: no-cover

        from_minutes_ago = options["from_minutes_ago"]
        keep_alive = options["keep_alive"]

        while True:
            try:
                self.get_updates(from_minutes_ago)
            except Exception as e:
                if not keep_alive:
                    raise CommandError from e
                logging.exception(e)
                self.get_updates(from_minutes_ago)

    def get_updates(self, from_minutes_ago: int) -> None:
        for url in podping.get_updates(from_minutes_ago):
            self.stdout.write(url)
