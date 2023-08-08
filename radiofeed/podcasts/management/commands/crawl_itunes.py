from typing import Final

import httpx
from django.core.management.base import BaseCommand

from radiofeed.client import http_client
from radiofeed.futures import DatabaseSafeThreadPoolExecutor
from radiofeed.podcasts import itunes

_LOCALES: Final = (
    "ar",
    "au",
    "br",
    "ca",
    "de",
    "es",
    "fi",
    "fr",
    "gb",
    "it",
    "jp",
    "no",
    "nz",
    "ru",
    "se",
    "us",
    "za",
)


class Command(BaseCommand):
    """Django management command."""

    help = """Crawls iTunes for new podcasts."""

    def handle(self, **options):
        """Handle implementation."""

        with http_client() as client, DatabaseSafeThreadPoolExecutor() as executor:
            executor.db_safe_map(
                lambda locale: self._crawl_feeds(client, locale), _LOCALES
            )

    def _crawl_feeds(self, client: httpx.Client, locale: str):
        for feed in itunes.crawl(client, locale):
            style = self.style.SUCCESS if feed.podcast is None else self.style.NOTICE
            self.stdout.write(style(feed.title))
