from __future__ import annotations

import requests

from django.core.management.base import BaseCommand, CommandError

from podtracker.podcasts import itunes


class Command(BaseCommand):
    help = "Crawl iTunes for new podcast feeds"

    def handle(self, *args, **options) -> None:
        try:
            for feed in itunes.crawl():
                self.stdout.write(feed.title)
        except requests.RequestException as e:
            raise CommandError from e
