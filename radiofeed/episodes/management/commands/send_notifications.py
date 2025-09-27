from datetime import datetime, timedelta

from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.db.models import (
    Count,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Window,
)
from django.db.models.functions import RowNumber
from django.utils import timezone

from radiofeed.episodes.models import Episode
from radiofeed.podcasts.models import Podcast
from radiofeed.users.emails import get_recipients, send_notification_email
from radiofeed.users.models import User


class Command(BaseCommand):
    """Send new episode notifications to users"""

    help = "Send new episode notifications to users"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments for the command"""
        parser.add_argument(
            "--num-episodes",
            type=int,
            default=6,
            help="Number of episodes to recommend per user",
        )

        parser.add_argument(
            "--num-days",
            type=int,
            default=7,
            help="Number of days since episodes published",
        )

    def handle(
        self,
        *,
        num_episodes: int,
        num_days: int,
        **options,
    ) -> None:
        """Handle the command execution"""
        """
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
        since = timezone.now() - timedelta(days=num_days)

        site = Site.objects.get_current()
        connection = get_connection()

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
        self, user: User, num_episodes: int, since: datetime
    ) -> QuerySet[Episode]:
        # group by query first

        return (
            Episode.objects.alias(
                is_subscribed=Exists(
                    user.subscriptions.filter(
                        podcast=OuterRef("podcast"),
                    ),
                ),
                is_recommended=Exists(
                    Podcast.objects.recommended(user).filter(pk=OuterRef("podcast"))
                ),
                num_listens=Subquery(
                    user.audio_logs.filter(episode__podcast=OuterRef("podcast"))
                    .values("episode__podcast")  # group by podcast
                    .annotate(cnt=Count("*"))  # count per podcast
                    .values("cnt")[:1],  # select just the count
                    output_field=IntegerField(),
                ),
                is_bookmarked=Exists(
                    user.bookmarks.filter(episode=OuterRef("pk")),
                ),
                is_listened=Exists(
                    user.audio_logs.filter(episode=OuterRef("pk")),
                ),
                rn=Window(
                    expression=RowNumber(),
                    partition_by=[F("podcast_id")],
                    order_by=F("pub_date").desc(),
                ),
            )
            .filter(
                Q(is_subscribed=True) | Q(is_recommended=True),
                is_listened=False,
                is_bookmarked=False,
                pub_date__lt=since,
                rn=1,
            )
            .select_related("podcast")
            .order_by(
                "podcast",
                "-num_listens",
                "-is_subscribed",
                "-pub_date",
            )[:num_episodes]
        )
