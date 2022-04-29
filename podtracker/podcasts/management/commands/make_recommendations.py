from __future__ import annotations

from django.core.management.base import BaseCommand

from podtracker.podcasts import recommender


class Command(BaseCommand):
    help = "Updates all podcasts from their RSS feeds."

    def handle(self, *args, **options) -> None:
        recommender.recommend()
