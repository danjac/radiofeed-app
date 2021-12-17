from __future__ import annotations

import argparse
import itertools
import logging

from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import podping


class Command(BaseCommand):
    help = "Runs Podping.cloud client"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--from",
            help="Start block minutes ago",
            type=int,
            default=15,
        )

    def handle(self, *args, **options) -> None:
        for _ in itertools.count():
            try:
                podping.run(timedelta(minutes=options["from"]))
            except Exception as e:
                logging.exception(e)
