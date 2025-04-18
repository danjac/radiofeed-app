import djclick as click
from allauth.account.models import EmailAddress
from django.core.mail import get_connection
from django.db import transaction

from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool
from radiofeed.users.emails import get_recipients, send_notification_email


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
    connection = get_connection()
    for future in execute_thread_pool(
        lambda recipient: _send_recommendations_email(
            recipient,
            num_podcasts,
            connection=connection,
        ),
        get_recipients(addresses),
    ):
        try:
            future.result()
        except Exception as e:
            click.secho(f"Error: {e}", fg="red")
            continue


def _send_recommendations_email(
    recipient: EmailAddress,
    num_podcasts: int,
    **kwargs,
) -> None:
    if podcasts := (
        Podcast.objects.published()
        .recommended(recipient.user)
        .order_by(
            "-relevance",
            "-promoted",
            "-pub_date",
        )
    )[:num_podcasts]:
        with transaction.atomic():
            click.secho(
                f"Sending {len(podcasts)} recommendations to {recipient.email}",
                fg="green",
            )

            send_notification_email(
                recipient,
                f"Hi, {recipient.user.name}, here are some podcasts you might like!",
                "podcasts/emails/recommendations.html",
                {
                    "podcasts": podcasts,
                },
                **kwargs,
            )

            recipient.user.recommended_podcasts.add(*podcasts)
