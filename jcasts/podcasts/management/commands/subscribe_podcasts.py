from __future__ import annotations

import argparse

from django.core.management.base import BaseCommand

from jcasts.podcasts import websub
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Subscribes podcasts to websub hub"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:

        parser.add_argument(
            "--clear-exceptions",
            help="Clear all websub errors before subscribing",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options) -> None:
        if options["clear_exceptions"]:
            Podcast.objects.filter(websub_status=Podcast.WebSubStatus.ERROR).update(
                websub_status=None,
                websub_exception="",
                websub_callback_exception="",
            )
        websub.subscribe_podcasts()
