from argparse import ArgumentParser

import requests
from django.core.management.base import BaseCommand

from radiofeed.futures import ThreadPoolExecutor
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
            executor.safemap(
                self._subscribe,
                subscriber.get_subscriptions_for_update().values_list("pk", flat=True)[
                    : options["limit"]
                ],
            )

    def _subscribe(self, subscription_id: int) -> None:
        subscription = Subscription.objects.select_related("podcast").get(
            pk=subscription_id
        )
        try:
            subscriber.subscribe(subscription)
            self.stdout.write(self.style.SUCCESS(f"subscribe: {subscription}"))
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"subscribe error {e}:{subscription}"))
