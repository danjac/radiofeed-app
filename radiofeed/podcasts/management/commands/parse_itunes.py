from argparse import ArgumentParser
from typing import Final

from django.core.management.base import BaseCommand

from radiofeed.podcasts.itunes import ItunesCatalogParser
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor

_DEFAULT_LOCALES: Final = (
    "ar",
    "at",
    "au",
    "bg",
    "be",
    "br",
    "ca",
    "cn",
    "cz",
    "de",
    "dk",
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
    "kr",
    "nl",
    "no",
    "nz",
    "pl",
    "ro",
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
        with DatabaseSafeThreadPoolExecutor() as executor:
            executor.db_safe_map(self._crawl_feeds, options["locales"])

    def _crawl_feeds(self, locale: str):
        for feed in ItunesCatalogParser(locale=locale).parse():
            style = self.style.SUCCESS if feed.podcast is None else self.style.NOTICE
            self.stdout.write(style(feed.title))
