from datetime import datetime, timedelta

from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.db import models
from django.db.models.functions import Coalesce, RowNumber
from django.utils import timezone

from radiofeed.episodes.models import Episode
from radiofeed.users.emails import get_recipients, send_notification_email
from radiofeed.users.models import User


class Command(BaseCommand):
    """Send new episode notifications to users"""

    help = "Send new episode notifications to users"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments for the command"""
        parser.add_argument(
            "--num-episodes",
            "-n",
            type=int,
            default=6,
            help="Number of episodes to recommend per user",
        )

        parser.add_argument(
            "--days_since",
            "-d",
            type=int,
            default=7,
            help="Period (days) since episodes published",
        )

    def handle(
        self,
        *,
        num_episodes: int,
        days_since: int,
        **options,
    ) -> None:
        """Handle the command execution
        Send list of episodes from past X days:

        1) from user's subscriptions
        2) do not include podcasts user has listened to in last X days
        3) if no episodes, pull from recommendations
        4) max num_episodes
        5) must be from different podcasts
        6) exclude listened or bookmarked episodes

        order by:
        1) podcast most times listened
        2) is subscribed
        """

        site = Site.objects.get_current()
        connection = get_connection()

        since = timezone.now() - timedelta(days=days_since)

        for recipient in get_recipients():
            if episodes := self._get_episodes(recipient.user, num_episodes, since):
                send_notification_email(
                    site,
                    recipient,
                    f"Hi, {recipient.user.name}, here are some episodes you might have missed!",
                    "episodes/emails/notifications.html",
                    {
                        "episodes": episodes,
                    },
                    connection=connection,
                )

                self.stdout.write(f"Notifications sent to {recipient.email}")

    def _get_episodes(
        self,
        user: User,
        num_episodes: int,
        since: datetime,
    ) -> models.QuerySet[Episode]:
        return (
            Episode.objects.subscribed(user)
            .alias(
                # show one episode per podcast
                # fetch only latest episode for the podcast
                row_number=models.Window(
                    expression=RowNumber(),
                    partition_by=[models.F("podcast_id")],
                    order_by=models.F("pub_date").desc(),
                ),
                # has bookmarked this episode
                is_bookmarked=models.Exists(
                    user.bookmarks.filter(episode=models.OuterRef("pk")),
                ),
                # has listened to any episode in this podcast within time period
                is_listened=models.Exists(
                    user.audio_logs.filter(
                        episode__podcast=models.OuterRef("podcast"),
                        listened__gt=since,
                    ),
                ),
                # number of times user has listened to podcast
                num_listens=Coalesce(
                    models.Subquery(
                        user.audio_logs.filter(
                            episode__podcast=models.OuterRef("podcast")
                        )
                        .values("episode__podcast")  # group by podcast
                        .annotate(listens=models.Count("*"))  # count per podcast
                        .values("listens")[:1],  # select just the count
                        output_field=models.IntegerField(),
                    ),
                    models.Value(0),
                ),
            )
            .filter(
                row_number=1,
                is_bookmarked=False,
                is_listened=False,
                pub_date__gt=since,
            )
            .select_related("podcast")
            .order_by("-num_listens")[:num_episodes]
        )
