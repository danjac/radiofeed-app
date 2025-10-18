from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool
from radiofeed.users.emails import get_recipients, send_notification_email
from radiofeed.users.models import User


class Command(BaseCommand):
    """Send podcast recommendations to users"""

    help = "Send podcast recommendations to users"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments for the command"""
        parser.add_argument(
            "--num-podcasts",
            type=int,
            default=6,
            help="Number of podcasts to recommend per user",
        )

    def handle(self, *, num_podcasts: int, **options) -> None:
        """Handle the command execution"""
        site = Site.objects.get_current()
        connection = get_connection()

        def _send_recommendations(recipient):
            if podcasts := self._get_podcasts(recipient.user, num_podcasts):
                send_notification_email(
                    site,
                    recipient,
                    f"Hi, {recipient.user.name}, here are some podcasts you might like!",
                    "podcasts/emails/recommendations.html",
                    {
                        "podcasts": podcasts,
                    },
                    connection=connection,
                )

                recipient.user.recommended_podcasts.add(*podcasts)
                self.stdout.write(
                    self.style.SUCCESS(f"Recommendations sent to {recipient.email}")
                )

        execute_thread_pool(_send_recommendations, get_recipients())

    def _get_podcasts(self, user: User, limit: int) -> QuerySet[Podcast]:
        return (
            Podcast.objects.published()
            .recommended(user)
            .order_by("-relevance", "promoted", "-pub_date")[:limit]
        )
