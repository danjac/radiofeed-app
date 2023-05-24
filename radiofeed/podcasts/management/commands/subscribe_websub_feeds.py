import contextlib
from argparse import ArgumentParser

import requests
from django.core.management.base import BaseCommand
from django_rq import get_queue

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
        queue = get_queue("low")
        for podcast_id in websub.get_podcasts_for_subscribe().values_list(
            "pk", flat=True
        )[: options["limit"]]:
            queue.enqueue(self._subscribe, podcast_id)

    def _subscribe(self, podcast_id: int) -> None:
        podcast = Podcast.objects.get(pk=podcast_id)
        self.stdout.write(f"subscribe: {podcast}")
        with contextlib.suppress(requests.RequestException):
            websub.subscribe(podcast)
