from django.core.management.base import BaseCommand

from radiofeed.feedparser import scheduler


class Command(BaseCommand):
    """Scheduled RSS feeds for update."""

    help = """Schedules podcast feeds for update"""

    def handle(self, **options) -> None:
        """Command handler implementation."""

        if num_scheduled := scheduler.schedule_podcasts_for_update():
            self.stdout.write(
                self.style.SUCCESS(f"{num_scheduled} podcasts scheduled for update")
            )
