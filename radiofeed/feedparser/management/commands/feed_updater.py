from __future__ import annotations

import itertools
import logging
import multiprocessing

from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.feedparser import feed_parser, scheduler
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):

    help = """
    Parses RSS feeds of all scheduled podcasts.
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--limit",
            help="Max number of feeds for update",
            type=int,
            default=360,
        )

    def handle(self, *args, **options) -> None:
        """Command handler implementation."""
        with multiprocessing.pool.ThreadPool(
            processes=multiprocessing.cpu_count()
        ) as pool:
            pool.map(
                self.parse_feed,
                itertools.islice(
                    scheduler.scheduled_for_update(),
                    options["limit"],
                ),
            )

    def parse_feed(self, podcast: Podcast) -> None:
        try:
            feed_parser.FeedParser(podcast).parse()
        except Exception as e:
            logging.exception(e)
