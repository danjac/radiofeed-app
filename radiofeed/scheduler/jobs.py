from django.core.management import call_command

from radiofeed.scheduler import scheduler


# non-app specific jobs
#
@scheduler.scheduled_job("interval", id="clear_sessions", days=1)
def clear_sessions():
    """Clear stale Django sessions."""
    call_command("clearsessions")
