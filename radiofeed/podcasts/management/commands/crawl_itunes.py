from argparse import ArgumentParser
from typing import Final

import httpx
from django.core.management.base import BaseCommand

from radiofeed.client import http_client
from radiofeed.podcasts import itunes
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor

_DEFAULT_LOCALES: Final = (
    "ar",
    "at",
    "au",
    "be",
    "br",
    "ca",
    "cn",
    "de",
    "eg",
    "es",
    "fi",
    "fr",
    "gb",
    "hk",
    "hu",
    "ie",
    "il",
    "in",
    "is",
    "it",
    "jp",
    "nl",
    "no",
    "nz",
    "pl",
    "ru",
    "se",
    "th",
    "tr",
    "tw",
    "ua",
    "us",
    "za",
)


class Command(BaseCommand):
    """Django management command."""

    help = """Crawls iTunes for new podcasts."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--locales",
            help="List of locales",
            default=_DEFAULT_LOCALES,
            nargs="+",
        )

    def handle(self, **options):
        """Handle implementation."""
        with http_client() as client, DatabaseSafeThreadPoolExecutor() as executor:
            executor.db_safe_map(
                lambda locale: self._crawl_feeds(client, locale),
                options["locales"],
            )

    def _crawl_feeds(self, client: httpx.Client, locale: str):
        for feed in itunes.crawl(client, locale):
            style = self.style.SUCCESS if feed.podcast is None else self.style.NOTICE
            self.stdout.write(style(feed.title))
