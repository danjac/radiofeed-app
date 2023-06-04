from argparse import ArgumentParser
from concurrent.futures import wait

from django.core.management.base import BaseCommand

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
            if num_scheduled := scheduler.schedule_podcasts_for_update():
                self.stdout.write(f"{num_scheduled} podcasts queued for update")

            with ThreadPoolExecutor() as executor:
                futures = executor.safemap(
                    self._parse_feed,
                    scheduler.get_queued_podcasts().values_list("pk", flat=True)[
                        : options["limit"]
                    ],
                )

            wait(futures)

            if futures:
                self.stdout.write(f"{len(futures)} podcasts updated")

            if not options["watch"]:
                break

    def _parse_feed(self, podcast_id: int) -> None:
        podcast = Podcast.objects.get(pk=podcast_id)
        try:
            feed_parser.FeedParser(podcast).parse()
            self.stdout.write(self.style.SUCCESS(f"parse feed ok: {podcast}"))
        except FeedParserError as e:
            self.stderr.write(
                self.style.ERROR(f"parse feed {e.parser_error}: {podcast}")
            )
