from __future__ import annotations

from argparse import ArgumentParser
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    help = """
    Removes podcasts from queue by setting queued=NULL. Use this
    for feeds that have timed out.
    """

    def add_arguments(self, parser: ArgumentParser) -> None:

        parser.add_argument(
            "--timeout", help="Timeout(seconds)", type=int, default=3600
        )

    def handle(self, *args, **kwargs):
        podcasts = Podcast.objects.filter(
            queued__isnull=False,
            queued__lt=timezone.now()
            - timedelta(
                seconds=kwargs["timeout"],
            ),
        )
        count = podcasts.count()
        podcasts.update(queued=None)
        self.stdout.write(f"{count} podcast(s) removed from queue")
