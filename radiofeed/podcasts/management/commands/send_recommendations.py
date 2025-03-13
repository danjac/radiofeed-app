import djclick as click
from allauth.account.models import EmailAddress

from radiofeed.podcasts import emails
from radiofeed.thread_pool import execute_thread_pool


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

    qs = EmailAddress.objects.filter(
        user__is_active=True,
        user__send_email_notifications=True,
    )
    if addresses:
        recipients = qs.filter(email__in=addresses)
    else:
        recipients = qs.filter(primary=True, verified=True)

    execute_thread_pool(emails.send_recommendations_email, recipients)
