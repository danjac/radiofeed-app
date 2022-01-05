from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from jcasts.episodes.emails import send_new_episodes_email


class Command(BaseCommand):
    help = "Email podcast recommendations to users"

    def handle(self, *args, **options) -> None:
        for user in get_user_model().objects.filter(
            send_email_notifications=True, is_active=True
        ):
            send_new_episodes_email.delay(user, timedelta(hours=24))
