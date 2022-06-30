import itertools

from django.core.management.base import BaseCommand
from django.db.models import Count, F

from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tasks import parse_feed


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", help="Number of feeds for update", type=int, default=360
        )

    def handle(self, *args, **options):
        parse_feed.map(
            itertools.islice(
                Podcast.objects.scheduled()
                .alias(subscribers=Count("subscription"))
                .order_by(
                    F("subscribers").desc(),
                    F("promoted").desc(),
                    F("parsed").asc(nulls_first=True),
                    F("pub_date").desc(nulls_first=True),
                )
                .values_list("pk")
                .distinct(),
                options["limit"],
            )
        )
