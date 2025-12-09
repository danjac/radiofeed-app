from typing import Annotated

import typer
from django_typer.management import Typer

from listenwave.podcasts.tasks import send_recommendations
from listenwave.users.emails import get_recipients

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

    for recipient_id in get_recipients().values_list("pk", flat=True):
        send_recommendations.enqueue(recipient_id=recipient_id, limit=limit)
