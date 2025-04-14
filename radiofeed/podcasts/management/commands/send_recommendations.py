import djclick as click

from radiofeed.podcasts import emails
from radiofeed.thread_pool import execute_thread_pool
from radiofeed.users.emails import get_recipients


@click.command()
@click.option(
    "--addresses",
    "-a",
    default=[],
    multiple=True,
    help="Emails to send recommendations to.",
)
def command(addresses: list[str]) -> None:
    """Send recommendation emails to users."""
    recipients = get_recipients()
    if addresses:
        recipients = recipients.filter(email__in=addresses)
    execute_thread_pool(emails.send_recommendations_email, recipients)
