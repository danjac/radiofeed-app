from __future__ import annotations

import argparse

from django.core.management.base import BaseCommand

from jcasts.podcasts import websub
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Subscribes podcasts to websub hub"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:

        parser.add_argument(
            "--clear",
            help="Clear all websub errors/requested before subscribing",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options) -> None:
        if options["clear"]:
            Podcast.objects.filter(
                websub_status__in=(
                    Podcast.WebSubStatus.ERROR,
                    Podcast.WebSubStatus.REQUESTED,
                )
            ).update(
                websub_status=None,
                websub_exception="",
                websub_status_changed=None,
            )
        websub.subscribe_podcasts()
