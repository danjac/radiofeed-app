from typing import Annotated

import typer
from django_typer.management import Typer

from listenwave.episodes.tasks import send_notifications
from listenwave.users.emails import get_recipients

app = Typer(help="Send notifications to users about new podcast episodes")


@app.command()
def handle(
    days_since: Annotated[
        int,
        typer.Option(
            "--days-since",
            "-d",
            help="Number of days to look back for new episodes",
        ),
    ] = 7,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Number of new podcast episodes to notify per user",
        ),
    ] = 6,
) -> None:
    """Handle the command execution"""
    for recipient_id in get_recipients().values_list("pk", flat=True):
        send_notifications.enqueue(
            recipient_id=recipient_id,
            days_since=days_since,
            limit=limit,
        )
