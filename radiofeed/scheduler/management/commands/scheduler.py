import argparse

from apscheduler.executors.pool import ThreadPoolExecutor
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.module_loading import autodiscover_modules
from django_apscheduler.jobstores import DjangoJobStore

from radiofeed.scheduler import scheduler


class Command(BaseCommand):
    """Command implementation for running the scheduler."""

    help = "Runs scheduler for all jobs."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments to the command parser."""
        parser.add_argument(
            "-t",
            "--threads",
            dest="num_threads",
            type=int,
            help="Number of threads to use for the scheduler.",
            default=10,
        )

    def handle(self, **options) -> None:
        """Runs scheduler.

        Should search all `INSTALLED_APPS` for a `jobs` module in each job.
        """

        # load all jobs across installed apps
        autodiscover_modules("jobs")

        # configure scheduler
        scheduler.configure(
            executors={
                "default": ThreadPoolExecutor(options["num_threads"]),
            },
            job_stores={
                "default": DjangoJobStore(),
            },
            timezone=settings.TIME_ZONE,
        )

        try:
            scheduler.start()
        except KeyboardInterrupt:
            scheduler.shutdown()
