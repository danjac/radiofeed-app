from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--frequency", help="Frequency between updates (minutes)", default=60
        )

    def handle(self, *args, **options):
        feed_parser.schedule_podcast_feeds(timedelta(minutes=options["frequency"]))
