from django.core.management.base import BaseCommand
from django.utils.module_loading import autodiscover_modules

from radiofeed.scheduler import scheduler


class Command(BaseCommand):
    """Command implementation for running the scheduler."""

    help = "Runs scheduler for all jobs."

    def handle(self, *args, **kwargs) -> None:
        """Runs scheduler.

        Should search all `INSTALLED_APPS` for a `jobs` module in each job.
        """

        autodiscover_modules("jobs")

        scheduler.start()
