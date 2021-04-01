from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from audiotrails.podcasts.emails import send_recommendations_email


class Command(BaseCommand):
    help = "Sends podcast recommendation emails"

    def handle(self, *args, **kwargs):
        users = get_user_model().objects.filter(
            send_recommendations_email=True, is_active=True
        )
        for user in users:
            send_recommendations_email(user)
