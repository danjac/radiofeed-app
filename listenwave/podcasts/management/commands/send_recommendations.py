from typing import Annotated

import typer
from allauth.account.models import EmailAddress
from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django_typer.management import Typer

from listenwave.podcasts.models import Podcast
from listenwave.thread_pool import execute_thread_pool
from listenwave.users.emails import get_recipients, send_notification_email

app = Typer(help="Send podcast recommendations to users")


@app.command()
def handle(
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Number of podcasts to recommend per user",
        ),
    ] = 6,
) -> None:
    """Handle the command execution"""

    site = Site.objects.get_current()
    connection = get_connection()

    def _send_recommendations(recipient: EmailAddress) -> None:
        if (
            podcasts := Podcast.objects.published()
            .recommended(recipient.user)
            .order_by("-relevance", "-pub_date")[:limit]
        ):
            send_notification_email(
                site,
                recipient,
                f"Hi, {recipient.user.name}, here are some podcasts you might like!",
                "podcasts/emails/recommendations.html",
                {
                    "podcasts": podcasts,
                },
                connection=connection,
            )

            recipient.user.recommended_podcasts.add(*podcasts)

            typer.secho(
                f"Podcast recommendations sent to to {recipient.email}",
                fg=typer.colors.GREEN,
            )

    recipients = get_recipients().select_related("user")
    execute_thread_pool(_send_recommendations, recipients)
