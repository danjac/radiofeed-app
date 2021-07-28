from django.core.management.base import BaseCommand

from jcasts.podcasts import tasks


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def handle(self, *args, **options) -> None:
        tasks.schedule_podcast_feeds.delay()
