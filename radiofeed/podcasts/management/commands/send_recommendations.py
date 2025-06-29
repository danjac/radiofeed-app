from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.core.management import CommandParser
from django.core.management.base import BaseCommand

from radiofeed.podcasts.models import Podcast
from radiofeed.users.emails import get_recipients, send_notification_email


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

        for recipient in get_recipients():
            if podcasts := (
                Podcast.objects.published()
                .recommended(recipient.user)
                .order_by("-relevance", "promoted", "-pub_date")
            )[:num_podcasts]:
                send_notification_email(
                    site,
                    recipient,
                    f"Hi, {recipient.user.name}, here are some podcasts you might like!",
                    "podcasts/emails/recommendations.html",
                    {
                        "podcasts": podcasts,
                        "site": site,
                    },
                    connection=connection,
                )

                recipient.user.recommended_podcasts.add(*podcasts)
                self.stdout.write(f"Recommendations sent to {recipient.email}")
