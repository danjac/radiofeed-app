from __future__ import annotations

import argparse

from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import scheduler


class Command(BaseCommand):
    help = "Schedule podcast feeds for polling"

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
        queue = options["queue"]
        limit = options["limit"]

        if options["primary"]:
            scheduler.schedule_primary_feeds(
                queue=queue,
                limit=limit,
            )
            return

        after = options["after"]
        before = options["before"]

        scheduler.schedule_secondary_feeds(
            after=timedelta(hours=after) if after else None,
            before=timedelta(hours=before) if before else None,
            queue=queue,
            limit=limit,
        )
