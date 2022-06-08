from django.core.management.base import BaseCommand

from radiofeed.podcasts import scheduler


class Command(BaseCommand):
    help = """
    Reschedules podcast update intervals
    """

    def handle(self, *args, **kwargs):
        count = scheduler.reschedule_podcast_feeds()
        self.stdout.write(self.style.SUCCESS(f"{count} podcast feeds rescheduled"))
