from django.core.management.base import BaseCommand

from jcasts.podcasts import scheduler


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def handle(self, *args, **options) -> None:
        scheduler.sync_podcast_feeds()
