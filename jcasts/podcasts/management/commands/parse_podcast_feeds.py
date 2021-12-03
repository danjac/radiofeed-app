from __future__ import annotations

import argparse

from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Parse podcast feeds"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--since",
            help="Hours since last parsed",
            type=int,
            default=None,
        )

        parser.add_argument(
            "--until",
            help="Hours until last parsed",
            type=int,
            default=None,
        )

        parser.add_argument(
            "--limit",
            help="Max limit of feeds",
            type=int,
            default=200,
        )

    def handle(self, *args, **options) -> None:

        feed_parser.parse_podcast_feeds(
            since=timedelta(hours=options["since"]) if options["since"] else None,
            until=timedelta(hours=options["until"]) if options["until"] else None,
            limit=options["limit"],
        )
