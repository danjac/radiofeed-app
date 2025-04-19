from django.core.management import call_command

from radiofeed.scheduler import scheduler


# non-app specific jobs
#
@scheduler.scheduled_job(
    "cron",
    id="clear_sessions",
    hour=2,
    minute=15,
)
def clear_sessions():
    """Clear stale Django sessions."""
    call_command("clearsessions")
