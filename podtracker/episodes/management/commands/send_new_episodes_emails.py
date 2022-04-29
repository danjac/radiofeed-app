from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand

from podtracker.episodes.emails import send_new_episodes_email
from podtracker.users.models import User


class Command(BaseCommand):
    help = "Email podcast recommendations to users"

    def handle(self, *args, **options) -> None:
        for user in User.objects.filter(send_email_notifications=True, is_active=True):
            send_new_episodes_email.delay(user, timedelta(days=7))
