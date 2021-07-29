from django.core.management.base import BaseCommand

from jcasts.podcasts import scheduler


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def handle(self, *args, **options) -> None:
        num_scheduled = scheduler.schedule_podcast_feeds()
        self.stdout.write(self.style.SUCCESS(f"{num_scheduled} podcasts scheduled"))
