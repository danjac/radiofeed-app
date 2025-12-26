import datetime
import random

from allauth.account.models import EmailAddress
from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Exists, OuterRef, QuerySet
from django.utils import timezone

from simplecasts.episodes.models import Episode
from simplecasts.thread_pool import db_threadsafe, thread_pool_map
from simplecasts.users.models import User
from simplecasts.users.notifications import get_recipients, send_notification_email


class Command(BaseCommand):
    """Send notifications to users about new podcast episodes."""

    help = "Send notifications to users about new podcast episodes"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command arguments."""
        parser.add_argument(
            "--days-since",
            "-d",
            type=int,
            default=7,
            help="Number of days to look back for new episodes",
        )
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=6,
            help="Number of new podcast episodes to notify per user",
        )

    def handle(self, *, days_since: int, limit: int, **options) -> None:
        """Handler implementation."""

        since = timezone.now() - datetime.timedelta(days=days_since)

        site = Site.objects.get_current()
        connection = get_connection()

        @db_threadsafe
        def _worker(recipient: EmailAddress) -> tuple[EmailAddress, bool]:
            if episodes := self._get_new_episodes(
                recipient.user, since=since, limit=limit
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
                return recipient, True
            return recipient, False

        recipients = get_recipients().select_related("user")

        for recipient, sent in thread_pool_map(_worker, recipients):
            if sent:
                self.stdout.write(f"Sent episode notifications to {recipient.email}")

    def _get_new_episodes(
        self,
        user: User,
        *,
        since: datetime.datetime,
        limit: int,
    ) -> QuerySet[Episode]:
        # Fetch latest episode IDs for each podcast the user is subscribed to since given time
        # Exclude any that the user has bookmarked or listened to
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
        if episode_ids := list(episodes.values()):
            sample_ids = random.sample(episode_ids, min(len(episode_ids), limit))
            return (
                Episode.objects.filter(pk__in=sample_ids)
                .select_related("podcast")
                .order_by("-pub_date", "-pk")
            )
        return Episode.objects.none()
