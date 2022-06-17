from __future__ import annotations

from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.podcasts import recommender
from radiofeed.podcasts.tasks import recommendations_email
from radiofeed.users.models import User


class Command(BaseCommand):
    help = """
    Runs recommendation algorithm.
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--email",
            help="Send email recommendations",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options) -> None:
        if options["email"]:
            recommendations_email.map(
                User.objects.email_notification_recipients().values_list("pk")
            )
        else:
            recommender.recommend()
