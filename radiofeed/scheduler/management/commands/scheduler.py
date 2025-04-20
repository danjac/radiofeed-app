from django.core.management.base import BaseCommand
from django.utils.module_loading import autodiscover_modules
from django_apscheduler.jobstores import DjangoJobStore

from radiofeed.scheduler import scheduler


class Command(BaseCommand):
    """Command implementation for running the scheduler."""

    help = "Runs scheduler for all jobs."

    def handle(self, **options) -> None:
        """Runs scheduler.

        Should search all `INSTALLED_APPS` for a `jobs` module in each job.
        """

        autodiscover_modules("jobs")

        scheduler.add_jobstore(DjangoJobStore(), "default")

        try:
            scheduler.start()
        except KeyboardInterrupt:
            scheduler.shutdown()
