from django.core.management.base import BaseCommand

from radiofeed.podcasts import recommender
from radiofeed.podcasts.tasks import send_recommendations_email
from radiofeed.users.models import User


class Command(BaseCommand):
    help = """
    Runs recommendation algorithms.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            help="Send recommendations emails to users",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options):
        if options["email"]:
            send_recommendations_email.map(
                User.objects.email_notification_recipients().values_list("pk")
            )
        else:
            recommender.recommend()
