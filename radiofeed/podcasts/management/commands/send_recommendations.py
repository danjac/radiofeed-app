from allauth.account.models import EmailAddress
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool
from radiofeed.users.emails import get_recipients, send_notification_email


class Command(BaseCommand):
    """Command implementation."""

    help = "Send podcast recommendations to users"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments."""
        parser.add_argument(
            "-n",
            "--num-podcasts",
            type=int,
            default=6,
            help="Number of podcasts to recommend",
        )

    def handle(self, **options) -> None:
        """Handle implementation."""
        connection = get_connection()
        execute_thread_pool(
            lambda recipient: self._send_recommendations_email(
                recipient,
                options["num_podcasts"],
                connection=connection,
            ),
            get_recipients(),
        )

    def _send_recommendations_email(
        self,
        recipient: EmailAddress,
        num_podcasts: int,
        **kwargs,
    ) -> None:
        if podcasts := (
            Podcast.objects.published()
            .recommended(recipient.user)
            .order_by(
                "-relevance",
                "-promoted",
                "-pub_date",
            )
        )[:num_podcasts]:
            with transaction.atomic():
                send_notification_email(
                    recipient,
                    f"Hi, {recipient.user.name}, here are some podcasts you might like!",
                    "podcasts/emails/recommendations.html",
                    {
                        "podcasts": podcasts,
                    },
                    **kwargs,
                )

                recipient.user.recommended_podcasts.add(*podcasts)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{len(podcasts)} recommendations sent to {recipient.email}"
                    )
                )
