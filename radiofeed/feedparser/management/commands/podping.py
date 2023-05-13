import json
import re
from argparse import ArgumentParser
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Final

import beem
from beem.blockchain import Blockchain
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from radiofeed.feedparser import feed_parser
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.iterators import batcher
from radiofeed.podcasts.models import Podcast

_OPERATION_ID_RE: Final = re.compile(r"^pp_(.*)_(.*)|podping$")


class Command(BaseCommand):
    """Runs a Podping.cloud watcher"""

    help = """Runs Podping.cloud watcher."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--rewind",
            help="Start from last block (minutes)",
            type=int,
            default=15,
        )

    def handle(self, **options) -> None:
        """Main command method."""

        blockchain = Blockchain(mode="head", blockchain_instance=beem.Hive())

        rewind_from = timedelta(minutes=options["rewind"])

        self._parse_feeds(
            self._parse_stream(
                blockchain.stream(
                    opNames=["custom_json"],
                    raw_ops=False,
                    threading=False,
                    start=blockchain.get_estimated_block_num(
                        timezone.now() - rewind_from
                    ),
                ),
            ),
            rewind_from,
        )

    def _parse_stream(self, stream: Iterator[dict]) -> Iterator[str]:
        for post in stream:
            if _OPERATION_ID_RE.match(post["id"]):
                data = json.loads(post["json"])

                yield from data.get("iris", [])
                yield from data.get("urls", [])

                if url := data.get("url"):
                    yield url

    def _parse_feeds(
        self,
        urls: Iterator[str],
        rewind_from: timedelta,
    ) -> None:
        for batch in batcher(urls, 100):
            with ThreadPoolExecutor() as executor:
                executor.map(
                    self._parse_feed,
                    Podcast.objects.filter(
                        Q(parsed__isnull=True)
                        | Q(parsed__lt=timezone.now() - rewind_from),
                        rss__in=set(batch),
                    ),
                )

    def _parse_feed(self, podcast: Podcast) -> None:
        try:
            feed_parser.FeedParser(podcast).parse(podping=True)

        except FeedParserError:
            self.stdout.write(self.style.ERROR(f"{podcast} not updated"))
        else:
            self.stdout.write(self.style.SUCCESS(f"{podcast} updated"))
