from __future__ import annotations

from django.core.management.base import BaseCommand

from jcasts.podcasts import websub


class Command(BaseCommand):
    help = "Send websub requests"

    def handle(self, *args, **options) -> None:
        websub.subscribe_podcasts()
