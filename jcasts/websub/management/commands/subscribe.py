from __future__ import annotations

from django.core.management.base import BaseCommand

from jcasts.websub import subscriber


class Command(BaseCommand):
    help = "Create or renew subscriptions"

    def handle(self, *args, **options) -> None:
        subscriber.enqueue()
