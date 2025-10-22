import random

from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef, QuerySet
from django.utils import timezone

from radiofeed.episodes.models import Episode
from radiofeed.thread_pool import execute_thread_pool
from radiofeed.users.emails import get_recipients, send_notification_email
from radiofeed.users.models import User


class Command(BaseCommand):
    """Send notifications to users about new podcast episodes"""

    help = "Send notifications to users about new podcast episodes"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments for the command"""
        parser.add_argument(
            "--num-episodes",
            "-n",
            type=int,
            default=6,
            help="Number of new podcast episodes to notify per user",
        )

        parser.add_argument(
            "--days-since",
            "-d",
            type=int,
            default=7,
            help="Number of days to look back for new episodes",
        )

    def handle(self, *, num_episodes: int, days_since: int, **options) -> None:
        """Handle the command execution"""
        site = Site.objects.get_current()
        connection = get_connection()

        def _send_notifications(recipient) -> None:
            if episodes := self._get_new_episodes(
                recipient.user, num_episodes, days_since
            ):
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

                self.stdout.write(
                    self.style.SUCCESS(f"Notifications sent to {recipient.email}")
                )

        execute_thread_pool(_send_notifications, get_recipients())

    def _get_new_episodes(
        self, user: User, limit: int, days_since: int
    ) -> QuerySet[Episode]:
        # Fetch episodes from podcasts the user is subscribed to that were published within the last `days_since` days
        # Order by the last pub date

        episode_ids = list(
            Episode.objects.annotate(
                is_bookmarked=Exists(user.bookmarks.filter(episode=OuterRef("pk"))),
                is_listened=Exists(user.audio_logs.filter(episode=OuterRef("pk"))),
                is_subscribed=Exists(
                    user.subscriptions.filter(podcast=OuterRef("podcast"))
                ),
            )
            .filter(
                is_bookmarked=False,
                is_listened=False,
                is_subscribed=True,
                pub_date__gte=timezone.now() - timezone.timedelta(days=days_since),
            )
            .values_list("pk", flat=True)
        )
        episode_ids = random.sample(episode_ids, min(len(episode_ids), limit))
        return Episode.objects.filter(pk__in=episode_ids).order_by("-pub_date", "-pk")
