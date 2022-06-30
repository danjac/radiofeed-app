import itertools

from django.core.management.base import BaseCommand

from radiofeed.podcasts import scheduler
from radiofeed.podcasts.tasks import parse_feed


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser):
        parser.add_argument("--limit", help="Limit", type=int, default=360)

    def handle(self, *args, **options):

        parse_feed.map(
            itertools.islice(
                scheduler.get_scheduled_feeds().values_list("pk").distinct(),
                options["limit"],
            )
        )
