from datetime import datetime

from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.db import models
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

        since = timezone.now() - timezone.timedelta(days=days_since)

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
    ) -> list[Episode]:
        is_listened = set(
            user.audio_logs.filter(listened__gt=since).values_list(
                "episode__podcast",
                flat=True,
            )
        )

        # get the latest episode from each podcast

        latest_episodes = dict(
            Episode.objects.subscribed(user)
            .filter(pub_date__gte=since)
            .exclude(podcast__in=is_listened)
            .order_by("podcast", "-pub_date", "-pk")
            .values_list("podcast", "pk")
        ).values()

        if not latest_episodes:
            return []

        # order by most listened podcasts first

        audio_counts = dict(
            user.audio_logs.values("episode__podcast")
            .annotate(listens=models.Count("*"))
            .values_list("episode__podcast", "listens")
        )

        episodes = Episode.objects.filter(pk__in=latest_episodes).select_related(
            "podcast"
        )

        return sorted(
            episodes,
            key=lambda e: (audio_counts.get(e.podcast_id, 0)),
        )[:num_episodes]
