from typing import TYPE_CHECKING, Annotated

import typer
from django_typer.management import Typer

from radiofeed.users import tasks
from radiofeed.users.notifications import get_recipients

app = Typer(help="Manage user notifications")


if TYPE_CHECKING:
    from allauth.account.models import EmailAddress
    from django.db.models import QuerySet


@app.command()
def podcast_recommendations(
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Max recommendations in email.",
        ),
    ] = 6,
):
    """Send podcast recommendations to users."""
    for recipient_id in _get_recipient_ids():
        tasks.send_podcast_recommendations.enqueue(
            recipient_id=recipient_id, limit=limit
        )


@app.command()
def episode_updates(
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Max episodes in email.",
        ),
    ] = 6,
):
    """Send episode updates to users."""
    for recipient_id in _get_recipient_ids():
        tasks.send_episode_updates.enqueue(recipient_id=recipient_id, limit=limit)


def _get_recipient_ids() -> QuerySet[EmailAddress]:
    return get_recipients().values_list("id", flat=True)
