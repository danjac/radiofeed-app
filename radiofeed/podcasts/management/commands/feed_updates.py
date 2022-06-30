import itertools

from django.core.management.base import BaseCommand

from radiofeed.podcasts import feed_scheduler
from radiofeed.podcasts.tasks import feed_update


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser):
        parser.add_argument("--limit", help="Limit", type=int, default=360)

    def handle(self, *args, **options):

        feed_update.map(
            itertools.islice(
                feed_scheduler.get_scheduled_feeds().values_list("pk").distinct(),
                options["limit"],
            )
        )
