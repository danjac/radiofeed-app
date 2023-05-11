import json
from argparse import ArgumentParser
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Final, TypedDict

import beem
from beem.account import Account
from beem.blockchain import Blockchain
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from radiofeed.feedparser import feed_parser
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.iterators import batcher
from radiofeed.podcasts.models import Podcast

ACCOUNT_NAME: Final = "podping"
MASTER_NODE: Final = "https://api.hive.blog"
WATCHED_OPERATION_IDS: Final = ("podping", "pp_")


class Post(TypedDict):
    """Post in blockchain stream."""

    id: str
    json: str
    required_posting_auths: list[str]


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

    def handle(self, *args, **kwargs) -> None:
        """Main command method."""
        allowed_accounts = self._get_allowed_accounts()

        blockchain = Blockchain(mode="head", blockchain_instance=beem.Hive())

        rewind_from = timedelta(minutes=kwargs["rewind"])

        self._parse_feeds(
            self._parse_stream(
                allowed_accounts,
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

    def _get_allowed_accounts(self) -> set[str]:
        return set(
            Account(
                ACCOUNT_NAME,
                blockchain_instance=beem.Hive(MASTER_NODE),
                lazy=True,
            ).get_following()
        )

    def _parse_stream(
        self, allowed_accounts: set[str], stream: Iterator[Post]
    ) -> Iterator[str]:
        for post in stream:
            if self._allowed_post(allowed_accounts, post):
                data = json.loads(post["json"])

                yield from data.get("iris", [])
                yield from data.get("urls", [])

                if url := data.get("url"):
                    yield url

    def _allowed_post(self, allowed_accounts: set[str], post: Post) -> bool:
        return any(
            post["id"].startswith(watched_id) for watched_id in WATCHED_OPERATION_IDS
        ) and bool(set(post["required_posting_auths"]) & allowed_accounts)

    def _parse_feeds(
        self,
        urls: Iterator[str],
        rewind_from: timedelta,
        batch_size: int = 100,
    ) -> None:
        for batch in batcher(urls, batch_size):
            with ThreadPoolExecutor() as executor:
                executor.map(
                    self._parse_feed,
                    Podcast.objects.filter(
                        Q(parsed__isnull=True)
                        | Q(parsed__lt=timezone.now() - rewind_from),
                        rss__in=batch,
                    ),
                )

    def _parse_feed(self, podcast: Podcast) -> None:
        try:
            feed_parser.FeedParser(podcast).parse()

        except FeedParserError:
            self.stdout.write(self.style.ERROR(f"{podcast} not updated"))
        else:
            self.stdout.write(self.style.SUCCESS(f"{podcast} updated"))
