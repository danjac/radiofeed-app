from __future__ import annotations

from django.core.management.base import BaseCommand

from radiofeed.podcasts import recommender


class Command(BaseCommand):
    """Django command."""

    help = """Runs recommendation algorithms."""

    def handle(self, *args, **options):
        """Command handler implementation."""
        recommender.recommend()
