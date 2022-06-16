from __future__ import annotations

from django.core.management.base import BaseCommand

from radiofeed.podcasts.tasks import send_recommendations_email
from radiofeed.users.models import User


class Command(BaseCommand):
    help = """
    Send recommendation emails
    """

    def handle(self, *args, **options) -> None:
        send_recommendations_email.map(
            User.objects.email_notification_recipients().values_list("pk")
        )
