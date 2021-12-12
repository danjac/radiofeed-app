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
            help="Hours after last parsed",
            type=int,
            default=None,
        )

        parser.add_argument(
            "--before",
            help="Hours before last parsed",
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
            "--primary",
            help="Followed or promoted podcasts",
            action="store_true",
        )

    def handle(self, *args, **options) -> None:

        after = timedelta(hours=options["after"]) if options["after"] else None
        before = timedelta(hours=options["before"]) if options["before"] else None

        feed_parser.parse_podcast_feeds(
            after=after,
            before=before,
            primary=options["primary"],
            queue=options["queue"],
            limit=options["limit"],
        )
