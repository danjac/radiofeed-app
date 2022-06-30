from django.core.management.base import BaseCommand

from radiofeed.podcasts import scheduler


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", help="Number of feeds for update", type=int, default=360
        )

    def handle(self, *args, **options):
        scheduler.schedule_feeds_for_update(options["limit"])
