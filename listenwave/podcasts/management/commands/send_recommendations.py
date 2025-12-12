from concurrent.futures import ThreadPoolExecutor

from allauth.account.models import EmailAddress
from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandParser

from listenwave.podcasts.models import Podcast
from listenwave.threadsafe import db_threadsafe
from listenwave.users.emails import get_recipients, send_notification_email


class Command(BaseCommand):
    """Send podcast recommendations to users."""

    help = "Send podcast recommendations to users"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command arguments."""
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=6,
            help="Number of podcasts to recommend per user",
        )

    def handle(self, *, limit: int, **options) -> None:
        """Handler implementation."""

        site = Site.objects.get_current()
        connection = get_connection()

        @db_threadsafe
        def _worker(recipient: EmailAddress) -> None:
            if (
                podcasts := Podcast.objects.published()
                .recommended(recipient.user)
                .order_by("-relevance", "-pub_date")[:limit]
            ):
                self.stdout.write(f"Sending recommendations to {recipient.email}")
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

        with ThreadPoolExecutor() as executor:
            for recipient in get_recipients().select_related("user"):
                executor.submit(_worker, recipient)
