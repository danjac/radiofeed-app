from __future__ import annotations

from django.core.management.base import BaseCommand

from podtracker.podcasts.emails import send_recommendations_email
from podtracker.users.models import User


class Command(BaseCommand):
    help = "Email podcast recommendations to users"

    def handle(self, *args, **options) -> None:
        for user in User.objects.filter(send_email_notifications=True, is_active=True):
            send_recommendations_email.delay(user)
