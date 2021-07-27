from django.core.management.base import BaseCommand

from jcasts.podcasts import tasks


class Command(BaseCommand):
    help = "Syncs podcast feeds"

    def handle(self, *args, **options) -> None:
        tasks.sync_frequent_podcast_feeds.delay()
