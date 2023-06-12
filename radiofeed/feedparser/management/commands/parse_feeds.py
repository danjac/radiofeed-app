from argparse import ArgumentParser
from concurrent.futures import Future, wait

from django.core.management.base import BaseCommand
from django.db.models import Count, F, QuerySet
from django.utils import timezone

from radiofeed.feedparser import feed_parser, scheduler
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.futures import ThreadPoolExecutor
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Parses RSS feeds."""

    help = """Parses RSS feeds of all scheduled podcasts."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--watch",
            help="Watch continuously",
            default=False,
            action="store_true",
        )

        parser.add_argument(
            "--limit",
            help="Number of feeds to process",
            type=int,
            default=360,
        )

    def handle(self, **options) -> None:
        """Command handler implementation."""

        while True:
            # get all scheduled podcasts
            podcasts = scheduler.get_scheduled_podcasts()

            # add any new items to queue
            if queued := self._enqueue_podcasts(podcasts):
                self.stdout.write(f"{queued} podcasts added to feed parser queue")

            # parse feeds
            wait(self._parse_feeds(podcasts, options["limit"]))

            if not options["watch"]:
                break

    def _enqueue_podcasts(self, podcasts: QuerySet[Podcast]) -> int:
        return podcasts.filter(queued__isnull=True).update(queued=timezone.now())

    def _parse_feeds(self, podcasts: QuerySet[Podcast], limit: int) -> list[Future]:
        # parse next n items in queue
        with ThreadPoolExecutor() as executor:
            return executor.safemap(
                self._parse_feed,
                podcasts.alias(subscribers=Count("subscriptions"))
                .filter(active=True, queued__isnull=False)
                .order_by(
                    F("subscribers").desc(),
                    F("promoted").desc(),
                    F("queued").asc(),
                    F("parsed").asc(nulls_first=True),
                )
                .values_list("pk", flat=True)
                .distinct()[:limit],
            )

    def _parse_feed(self, podcast_id: int) -> None:
        podcast = Podcast.objects.get(pk=podcast_id)
        try:
            feed_parser.FeedParser(podcast).parse()
            self.stdout.write(self.style.SUCCESS(f"parse feed ok: {podcast}"))
        except FeedParserError as e:
            self.stderr.write(
                self.style.ERROR(f"parse feed {e.parser_error}: {podcast}")
            )
