import datetime
import random
from datetime import timedelta
from typing import Annotated

import typer
from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.db.models import Exists, OuterRef, QuerySet
from django.utils import timezone
from django_typer.management import Typer

from listenwave.episodes.models import Episode
from listenwave.users.emails import get_recipients, send_notification_email
from listenwave.users.models import User

app = Typer(help="Send notifications to users about new podcast episodes")


@app.command()
def handle(
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Number of new podcast episodes to notify per user",
        ),
    ] = 6,
    days_since: Annotated[
        int,
        typer.Option(
            "--days-since",
            "-d",
            help="Number of days to look back for new episodes",
        ),
    ] = 7,
) -> None:
    """Handle the command execution"""
    site = Site.objects.get_current()
    since = timezone.now() - timedelta(days=days_since)
    connection = get_connection()

    for recipient in get_recipients():
        if episodes := _get_new_episodes(recipient.user, limit, since):
            send_notification_email(
                site,
                recipient,
                f"Hi, {recipient.user.name}, check out these new podcast episodes!",
                "episodes/emails/notifications.html",
                {
                    "episodes": episodes,
                },
                connection=connection,
            )

            typer.secho(
                f"{len(episodes)} episode notifications sent to {recipient.email}",
                fg=typer.colors.GREEN,
            )


def _get_new_episodes(
    user: User, limit: int, since: datetime.datetime
) -> QuerySet[Episode]:
    # Fetch latest episode IDs for each podcast the user is subscribed to
    # Exclude any that the user has bookmarked or listened to
    # Include only those published within the last `days_since` days
    episodes = dict(
        Episode.objects.annotate(
            is_bookmarked=Exists(
                user.bookmarks.filter(
                    episode=OuterRef("pk"),
                )
            ),
            is_listened=Exists(
                user.audio_logs.filter(
                    episode=OuterRef("pk"),
                )
            ),
            is_subscribed=Exists(
                user.subscriptions.filter(
                    podcast=OuterRef("podcast"),
                )
            ),
        )
        .filter(
            is_bookmarked=False,
            is_listened=False,
            is_subscribed=True,
            pub_date__gte=since,
        )
        .order_by("pub_date", "pk")
        .values_list("podcast", "pk")
    )
    # Randomly sample up to `limit` episode IDs
    episode_ids = list(episodes.values())
    sample_ids = random.sample(episode_ids, min(len(episode_ids), limit))
    return (
        Episode.objects.filter(pk__in=sample_ids)
        .select_related("podcast")
        .order_by("-pub_date", "-pk")
    )
