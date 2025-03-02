import djclick as click
from allauth.account.models import EmailAddress

from radiofeed.podcasts import emails
from radiofeed.thread_pool import execute_thread_pool


@click.command()
def command():
    """Send recommendation emails to users."""
    execute_thread_pool(
        emails.send_recommendations_email,
        EmailAddress.objects.filter(
            user__is_active=True,
            user__send_email_notifications=True,
            primary=True,
            verified=True,
        ),
    )
