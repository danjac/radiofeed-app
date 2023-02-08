from __future__ import annotations

from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand

from radiofeed.websub import subscriber
from radiofeed.websub.models import Subscription


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
                Subscription.objects.filter(requested__isnull=True)
                .select_related("podcast")[: options["limit"]]
                .order_by("-created")
                .iterator(),
            )

    def _subscribe(self, subscription: Subscription) -> None:
        self.stdout.write(f"Subscribing feed {subscription.podcast}...")
        subscriber.subscribe(subscription)
