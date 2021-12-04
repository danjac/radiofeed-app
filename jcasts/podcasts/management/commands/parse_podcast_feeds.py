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
            "--after",
            help="Days after last parsed",
            type=int,
            default=None,
        )

        parser.add_argument(
            "--before",
            help="Days before last parsed",
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

        parser.add_argument(
            "--promoted",
            help="Followed podcasts",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options) -> None:

        after = timedelta(days=options["after"]) if options["after"] else None
        before = timedelta(days=options["before"]) if options["before"] else None

        feed_parser.parse_podcast_feeds(
            after=after,
            before=before,
            followed=options["followed"],
            promoted=options["promoted"],
            queue=options["queue"],
            limit=options["limit"],
        )
