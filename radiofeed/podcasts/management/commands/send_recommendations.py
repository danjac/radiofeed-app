from typing import Annotated

import typer
from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.db.models import QuerySet
from django_typer.management import Typer

from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool
from radiofeed.users.emails import get_recipients, send_notification_email
from radiofeed.users.models import User

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

    def _send_recommendations(recipient) -> None:
        if podcasts := _get_podcasts(recipient.user, limit):
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
                f"{len(podcasts)} podcast recommendations sent to {recipient.email}",
                fg=typer.colors.GREEN,
            )

    execute_thread_pool(_send_recommendations, get_recipients())


def _get_podcasts(user: User, num_podcasts: int) -> QuerySet[Podcast]:
    return (
        Podcast.objects.published()
        .recommended(user)
        .order_by(
            "-relevance",
            "-promoted",
            "-pub_date",
        )[:num_podcasts]
    )
