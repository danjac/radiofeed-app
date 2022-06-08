from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand

from radiofeed.episodes.tasks import send_new_episodes_email
from radiofeed.users.models import User


class Command(BaseCommand):
    help = """
    Send new episodes notification emails
    """

    def handle(self, *args, **kwargs) -> None:
        send_new_episodes_email.map(
            [
                (user_id, timedelta(days=7))
                for user_id in User.objects.filter(
                    send_email_notifications=True, is_active=True
                ).values_list("pk", flat=True)
            ]
        )
