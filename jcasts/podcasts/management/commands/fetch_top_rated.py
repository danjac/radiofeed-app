from __future__ import annotations

import requests

from django.core.management.base import BaseCommand, CommandError

from jcasts.podcasts import itunes


class Command(BaseCommand):
    help = "Fetch top rated feeds"

    def handle(self, *args, **options) -> None:
        try:
            for feed in itunes.top_rated():
                self.stdout.write(feed.title)
        except requests.RequestException as e:
            raise CommandError from e
