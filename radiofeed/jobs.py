from django.core.management import call_command
from scheduler import job


@job
def clear_sessions():
    """Clears expired sessions."""
    call_command("clearsessions")
