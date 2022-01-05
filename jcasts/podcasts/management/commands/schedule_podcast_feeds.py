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
        schedule = (
            scheduler.schedule_primary_feeds
            if options["primary"]
            else scheduler.schedule_secondary_feeds
        )

        count = schedule(
            after=timedelta(hours=options["after"]) if options["after"] else None,
            before=timedelta(hours=options["before"]) if options["before"] else None,
            queue=options["queue"],
            limit=options["limit"],
        )

        self.stdout.write(self.style.SUCCESS(f"{count} feed(s) scheduled for update"))
