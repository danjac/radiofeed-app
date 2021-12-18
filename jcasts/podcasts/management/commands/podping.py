from __future__ import annotations

import argparse
import itertools
import logging

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError

from jcasts.podcasts import podping


class Command(BaseCommand):
    help = "Runs Podping.cloud client"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--from",
            help="Start block from minutes ago",
            type=int,
            default=15,
        )

        parser.add_argument(
            "--restart-on-failure",
            help="Restart on error",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options) -> None:
        for _ in itertools.count():
            try:
                for url in podping.run(timedelta(minutes=options["from"])):
                    self.stdout.write(url)
            except Exception as e:
                if options["restart_on_failure"]:
                    logging.exception(e)
                else:
                    raise CommandError from e
