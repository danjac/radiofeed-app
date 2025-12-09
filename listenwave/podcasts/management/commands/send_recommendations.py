from typing import Annotated

import typer
from django.contrib.sites.models import Site
from django_typer.management import Typer

from listenwave.podcasts.models import Podcast
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

    for recipient in get_recipients().select_related("user"):
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
            )

            recipient.user.recommended_podcasts.add(*podcasts)
            typer.secho(
                f"Podcast recommendations sent to to {recipient.email}",
                fg=typer.colors.GREEN,
            )
