from __future__ import annotations

from django.core.management.base import BaseCommand

from jcasts.podcasts import websub


class Command(BaseCommand):
    help = "Subscribes podcasts to websub hub"

    def handle(self, *args, **options) -> None:
        websub.subscribe_podcasts()
