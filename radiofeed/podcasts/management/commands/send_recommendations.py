from allauth.account.models import EmailAddress
from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.db import transaction

from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool
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

        execute_thread_pool(
            lambda recipient: self._send_recommendations_email(
                recipient,
                site,
                num_podcasts,
                connection=connection,
            ),
            get_recipients(),
        )

    def _send_recommendations_email(
        self,
        recipient: EmailAddress,
        site: Site,
        num_podcasts: int,
        **kwargs,
    ):
        if podcasts := (
            Podcast.objects.published()
            .recommended(recipient.user)
            .order_by(
                "-relevance",
                "promoted",
                "-pub_date",
            )
        )[:num_podcasts]:
            with transaction.atomic():
                send_notification_email(
                    site,
                    recipient,
                    f"Hi, {recipient.user.name}, here are some podcasts you might like!",
                    "podcasts/emails/recommendations.html",
                    {
                        "podcasts": podcasts,
                        "site": site,
                    },
                    **kwargs,
                )

                recipient.user.recommended_podcasts.add(*podcasts)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{num_podcasts} recommendations sent to {recipient.email}"
                    )
                )
