from __future__ import annotations

import argparse

from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Parse podcast feeds"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--queue",
            help="Job queue",
            type=str,
            default="feeds",
        )

        parser.add_argument(
            "--since",
            help="Days since last parsed",
            type=int,
            default=None,
        )

        parser.add_argument(
            "--until",
            help="Days until last parsed",
            type=int,
            default=None,
        )

        parser.add_argument(
            "--limit",
            help="Max limit of feeds",
            type=int,
            default=200,
        )

        parser.add_argument(
            "--followed",
            help="Followed podcasts",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options) -> None:

        since = timedelta(days=options["since"]) if options["since"] else None
        until = timedelta(days=options["until"]) if options["until"] else None

        feed_parser.parse_podcast_feeds(
            since=since,
            until=until,
            followed=options["followed"],
            queue=options["queue"],
            limit=options["limit"],
        )
