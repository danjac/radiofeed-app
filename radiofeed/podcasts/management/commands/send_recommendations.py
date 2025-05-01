from typing import Annotated

from allauth.account.models import EmailAddress
from django.core.mail import get_connection
from django.db import transaction
from django_typer.management import TyperCommand
from typer import Option

from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool
from radiofeed.users.emails import get_recipients, send_notification_email


class Command(TyperCommand):
    """Management command to send podcast recommendations to users."""

    def handle(
        self,
        num_podcasts: Annotated[
            int,
            Option(
                "-n",
                "--num-podcasts",
                help="Number of podcasts to recommend",
            ),
        ] = 6,
    ) -> None:
        """Send podcast recommendations to users"""
        connection = get_connection()
        execute_thread_pool(
            lambda recipient: self._send_recommendations_email(
                recipient,
                num_podcasts,
                connection=connection,
            ),
            get_recipients(),
        )

    def _send_recommendations_email(
        self, recipient: EmailAddress, num_podcasts: int, **kwargs
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
                    ),
                )
