from django.core.management.base import BaseCommand

from jcasts.podcasts.tasks import sync_podcast_feeds


class Command(BaseCommand):
    help = "Schedules podcast feeds"

    def handle(self, *args, **options) -> None:
        sync_podcast_feeds.delay()
