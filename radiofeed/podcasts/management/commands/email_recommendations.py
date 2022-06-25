from django.core.management.base import BaseCommand

from radiofeed.podcasts.tasks import send_recommendations_email
from radiofeed.users.models import User


class Command(BaseCommand):
    help = """
    Sends recommendations emails to users
    """

    def handle(self, *args, **options):
        send_recommendations_email.map(
            User.objects.email_notification_recipients().values_list("pk")
        )
