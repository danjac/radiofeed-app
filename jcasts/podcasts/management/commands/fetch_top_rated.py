from __future__ import annotations

from django.core.management.base import BaseCommand

from jcasts.podcasts import itunes


class Command(BaseCommand):
    help = "Fetch top rated feeds"

    def handle(self, *args, **options) -> None:
        itunes.top_rated()
