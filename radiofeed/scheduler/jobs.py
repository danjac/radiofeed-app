import logging

from django.core.management import call_command
from django.utils import timezone
from django_apscheduler.models import DjangoJobExecution

from radiofeed.scheduler import scheduler

logger = logging.getLogger(__name__)


# non-app specific jobs
#
@scheduler.scheduled_job(
    "cron",
    id="scheduler.clear_sessions",
    hour=2,
    minute=15,
)
def clear_sessions():
    """Clear stale Django sessions."""
    logger.info("Clearing stale Django sessions")
    call_command("clearsessions")


@scheduler.scheduled_job(
    "cron",
    id="scheduler.delete_old_job_executions",
    hour=3,
    minute=33,
)
def delete_old_job_executions():
    """Delete old job connections older than 24 hours"""
    executions = DjangoJobExecution.objects.filter(
        run_time__lt=timezone.now() - timezone.timedelta(days=1)
    )
    num_executions = executions.count()
    executions.delete()
    logger.info("Deleted %d old job executions", num_executions)
