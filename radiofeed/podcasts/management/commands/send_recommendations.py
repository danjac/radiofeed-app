import djclick as click
from django.core.mail import get_connection

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
@click.option(
    "--num_podcasts",
    "-n",
    default=6,
    help="Max number of podcasts to recommend.",
)
def command(addresses: list[str], num_podcasts: int) -> None:
    """Send recommendation emails to users."""

    recipients = get_recipients()

    if addresses:
        recipients = recipients.filter(email__in=addresses)

    if num_recipients := recipients.count():
        connection = get_connection()
        click.secho(f"Sending emails to {num_recipients} recipient(s)", fg="green")
        execute_thread_pool(
            lambda recipient: emails.send_recommendations_email(
                recipient,
                num_podcasts,
                connection=connection,
            ),
            recipients,
        )
    else:
        click.secho("No recipients found", fg="yellow")
