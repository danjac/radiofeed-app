import collections
from datetime import datetime

from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.core.management import CommandParser
from django.core.management.base import BaseCommand
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
        Send list of [num_episodes] episodes from past [days_since]:

        1) from user's subscriptions
        2) do not include podcasts user has listened to in last X days
        3) must be from different podcasts
        4) exclude bookmarked episodes

        Order by frequency of user's listens to podcasts
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
        listened_podcasts = user.audio_logs.values(
            "episode__podcast",
            "listened",
        )

        is_listened = {
            p["episode__podcast"] for p in listened_podcasts if p["listened"] > since
        }

        is_bookmarked = set(
            user.bookmarks.values_list(
                "episode",
                flat=True,
            )
        )

        # get the latest episode from each podcast

        latest_episodes = dict(
            Episode.objects.subscribed(user)
            .filter(pub_date__gte=since)
            .exclude(podcast__in=is_listened)
            .exclude(pk__in=is_bookmarked)
            .order_by("podcast", "pub_date", "pk")
            .values_list("podcast", "pk")
        )

        if not latest_episodes:
            return []

        # order by most listened podcasts first

        audio_counts = collections.Counter(
            p["episode__podcast"] for p in listened_podcasts
        )

        episodes = Episode.objects.filter(
            pk__in=latest_episodes.values()
        ).select_related("podcast")

        return sorted(
            episodes,
            key=lambda e: audio_counts[e.podcast_id],
            reverse=True,
        )[:num_episodes]
