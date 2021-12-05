from __future__ import annotations

import argparse

from django.core.management.base import BaseCommand

# import logging

# from datetime import timedelta


# from jcasts.podcasts import podping


class Command(BaseCommand):
    help = "Calls podping blockchain to get latest updates"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--from-minutes-ago",
            type=int,
            default=15,
        )

    def handle(self, *args, **options) -> None:

        self.stdout.write("Starting podping")

        while True:
            pass

        # try:
        # for url in podping.get_updates(
        # timedelta(minutes=options["from_minutes_ago"])
        # ):
        # self.stdout.write(url)
        # except Exception as e:
        # logging.exception(e)
        # self.stderr.write(self.style.ERROR(f"error: {e}, restating..."))
