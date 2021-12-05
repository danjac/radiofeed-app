from __future__ import annotations

import argparse
import itertools

from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import podping


class Command(BaseCommand):
    help = "Calls podping blockchain to get latest updates"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--from-minutes-ago",
            type=int,
            default=15,
        )

    def handle(self, *args, **options) -> None:

        self.stdout.write("starting podping...")
        since = timedelta(minutes=options["from_minutes_ago"])

        for _ in itertools.count():
            self.get_updates(since)

    def get_updates(self, since: timedelta) -> None:
        try:
            for url in podping.get_updates(since):
                self.stdout.write(url)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"error: {e}, restarting podping..."))
