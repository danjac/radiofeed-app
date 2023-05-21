import json
import re
from argparse import ArgumentParser
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Final

import beem
from beem.blockchain import Blockchain
from beem.nodelist import NodeList
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from radiofeed.feedparser import feed_parser
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

        nodelist = NodeList()
        nodelist.update_nodes()

        blockchain = Blockchain(
            blockchain_instance=beem.Hive(
                node=nodelist.get_hive_nodes(),
                debug=True,
            ),
        )

        rewind_from = timedelta(minutes=options["rewind"])

        self._parse_stream(
            blockchain.stream(
                opNames=["custom_json"],
                raw_ops=False,
                threading=False,
                start=blockchain.get_estimated_block_num(timezone.now() - rewind_from),
            ),
            rewind_from,
        )

    def _parse_stream(self, stream: Iterator[dict], rewind_from: timedelta) -> None:
        for post in stream:
            if _OPERATION_ID_RE.match(post["id"]):
                data = json.loads(post["json"])

                urls: set[str] = set()

                urls = urls | set(data.get("iris", []))
                urls = urls | set(data.get("urls", []))

                if url := data.get("url"):
                    urls.add(url)

                if urls:
                    self._parse_feeds(urls, rewind_from)

    def _parse_feeds(self, urls: set[str], rewind_from: timedelta) -> None:
        self.stdout.write(f"Podping urls: {urls}")
        with ThreadPoolExecutor() as executor:
            executor.map(
                self._parse_feed,
                Podcast.objects.filter(
                    Q(parsed__isnull=True) | Q(parsed__lt=timezone.now() - rewind_from),
                    active=True,
                    rss__in=urls,
                ).iterator(),
            )

    def _parse_feed(self, podcast: Podcast) -> None:
        self.stdout.write(f"Podcast: {podcast}")
        feed_parser.parse_feed(podcast, podping=True)
