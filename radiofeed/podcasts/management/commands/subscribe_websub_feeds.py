import contextlib
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

import requests
from django.core.management.base import BaseCommand

from radiofeed.iterators import batcher
from radiofeed.podcasts import websub
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Subscribes new feeds to their websub hub."""

    help = """Subscribes new feeds to their websub hub."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--limit",
            help="Max number of feeds for update",
            type=int,
            default=360,
        )

    def handle(self, **options) -> None:
        """Command handler implementation."""
        for podcasts in batcher(
            websub.get_podcasts_for_subscribe()[: options["limit"]].iterator(), 30
        ):
            with ThreadPoolExecutor() as executor:
                executor.map(
                    self._subscribe,
                    podcasts,
                )

    def _subscribe(self, podcast: Podcast) -> None:
        self.stdout.write(f"Subscribe: {podcast}")
        with contextlib.suppress(requests.RequestException):
            websub.subscribe(podcast)
