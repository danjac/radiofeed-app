from __future__ import annotations

import argparse

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = """
    Clears any podcasts stuck in the queue. This sometimes happens e.g. when
    restarting workers in a deployment.
    """

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--since",
            help="Hours since podcasts queued",
            type=int,
            default=3,
        )

    def handle(self, *args, **options) -> None:
        Podcast.objects.filter(
            queued__lt=timezone.now() - timedelta(hours=options["since"])
        ).update(queued=None)
