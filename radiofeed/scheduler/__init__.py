from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from django.conf import settings
from django.core.management import call_command

scheduler = BlockingScheduler(
    executors={
        "default": ThreadPoolExecutor(20),
        "processpool": ProcessPoolExecutor(5),
    },
    timezone=settings.TIME_ZONE,
)


# non-app specific jobs
#
@scheduler.scheduled_job("interval", id="clear_sessions", days=1)
def clear_sessions():
    """Clear stale Django sessions."""
    call_command("clearsessions")
