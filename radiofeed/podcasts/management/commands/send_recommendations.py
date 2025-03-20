import djclick as click
from allauth.account.models import EmailAddress
from django.db.models import QuerySet

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

    execute_thread_pool(
        emails.send_recommendations_email,
        _get_recipients(addresses),
    )


def _get_recipients(addresses: list[str]) -> QuerySet[EmailAddress]:
    qs = EmailAddress.objects.filter(
        user__is_active=True,
        user__send_email_notifications=True,
    ).select_related("user")

    if addresses:
        return qs.filter(email__in=addresses)
    return qs.filter(primary=True, verified=True)
