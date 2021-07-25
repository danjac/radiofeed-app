from django.core.management.base import BaseCommand

from jcasts.podcasts.tasks import schedule_podcast_feeds


class Command(BaseCommand):
    help = "Schedules podcast feeds"

    def handle(self, *args, **options) -> None:
        schedule_podcast_feeds.delay()
