from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from jcasts.podcasts.emails import send_recommendations_email


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def handle(self, *args, **options) -> None:
        for user in get_user_model().objects.filter(
            send_recommendations_email=True, is_active=True
        ):
            send_recommendations_email.delay(user)
