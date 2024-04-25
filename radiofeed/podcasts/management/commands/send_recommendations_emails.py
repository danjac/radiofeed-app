import djclick as click

from radiofeed.podcasts import emails
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor
from radiofeed.users.models import User


@click.command(help="Command to send recommendations emails.")
def command() -> None:
    """Implementation of command."""

    with DatabaseSafeThreadPoolExecutor() as executor:
        executor.db_safe_map(
            emails.send_recommendations_email,
            User.objects.filter(
                is_active=True,
                send_email_notifications=True,
            ),
        )
