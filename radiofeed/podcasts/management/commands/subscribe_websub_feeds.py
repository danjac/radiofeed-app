from __future__ import annotations

from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

import requests

from django.core.management.base import BaseCommand

from radiofeed.podcasts import subscriber
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
        with ThreadPoolExecutor() as executor:
            executor.map(
                self._subscribe,
                subscriber.get_podcasts_for_subscribe()[: options["limit"]].iterator(),
            )

    def _subscribe(self, podcast: Podcast) -> None:
        self.stdout.write(f"Sending subscription request for {podcast}...")

        try:
            subscriber.subscribe(podcast)

        except requests.RequestException:
            self.stdout.write(self.style.ERROR(f"{podcast} request failed"))
        else:
            self.stdout.write(self.style.SUCCESS(f"{podcast} request sent"))
