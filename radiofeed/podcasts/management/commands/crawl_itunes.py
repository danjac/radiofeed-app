from __future__ import annotations

import httpx

from django.core.management.base import BaseCommand

from radiofeed.common.user_agent import user_agent
from radiofeed.podcasts import itunes


class Command(BaseCommand):
    """Django management command."""

    help = """Crawls iTunes for new podcasts."""

    def handle(self, **options):
        """Handle implementation."""
        with httpx.Client(headers={"User-Agent": user_agent()}, timeout=10) as client:

            for feed in itunes.crawl(client):
                style = (
                    self.style.SUCCESS if feed.podcast is None else self.style.NOTICE
                )
                self.stdout.write(style(feed.title))
