from argparse import ArgumentParser
from concurrent.futures import wait

import requests
from django.core.management.base import BaseCommand

from radiofeed.futures import ThreadPoolExecutor
from radiofeed.podcasts import websub
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Subscribes new feeds to their websub hub."""

    help = """Subscribes new feeds to their websub hub."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--watch",
            help="Watch continuously",
            default=False,
            action="store_true",
        )

        parser.add_argument(
            "--limit",
            help="Max number of feeds for update",
            type=int,
            default=360,
        )

    def handle(self, **options) -> None:
        """Command handler implementation."""

        while True:
            with ThreadPoolExecutor() as executor:
                futures = executor.safemap(
                    self._subscribe,
                    websub.get_podcasts_for_subscribe().values_list("pk", flat=True)[
                        : options["limit"]
                    ],
                )
            wait(futures)

            if not options["watch"]:
                break

    def _subscribe(self, podcast_id: int) -> None:
        podcast = Podcast.objects.get(pk=podcast_id)
        try:
            websub.subscribe(podcast)
            self.stdout.write(self.style.SUCCESS(f"subscribe: {podcast}"))
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"subscribe error {e}:{podcast}"))
