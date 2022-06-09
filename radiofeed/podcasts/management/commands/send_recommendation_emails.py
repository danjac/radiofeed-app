from __future__ import annotations

from django.core.management.base import BaseCommand

from radiofeed.podcasts.emails import send_recommendations_email
from radiofeed.users.models import User


class Command(BaseCommand):
    help = """
    Send recommendation emails
    """

    def handle(self, *args, **kwargs) -> None:
        for user_id in User.objects.email_notification_recipients().values_list(
            "pk", flat=True
        ):
            send_recommendations_email.delay(user_id)
