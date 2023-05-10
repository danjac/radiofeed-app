import json
from argparse import ArgumentParser
from datetime import datetime, timedelta

import beem
from beem.account import Account
from beem.blockchain import Blockchain
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from radiofeed.feedparser import feed_parser
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.podcasts.models import Podcast

ACCOUNT_NAME = "podping"
MASTER_NODE = "https://api.hive.blog"
WATCHED_OPERATION_IDS = ["podping", "pp_"]


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

        rewind_from = timezone.now() - timedelta(minutes=kwargs["rewind"])

        start_num = blockchain.get_estimated_block_num(rewind_from)

        stream = blockchain.stream(
            opNames=["custom_json"],
            raw_ops=False,
            threading=False,
            start=start_num,
        )

        for post in stream:
            if (
                self._allowed_op_id(post["id"])
                and set(post["required_posting_auths"]) & allowed_accounts
            ):
                data = json.loads(post.get("json")) or {}

                urls = set(data.get("iris", [])) | set(data.get("urls", []))

                if url := data.get("url"):
                    urls.add(url)

                self._parse_feeds(urls, rewind_from)

    def _allowed_op_id(self, op_id: str) -> bool:
        return any(op_id.startswith(watched_id) for watched_id in WATCHED_OPERATION_IDS)

    def _get_allowed_accounts(self) -> set[str]:
        return set(
            Account(
                ACCOUNT_NAME,
                blockchain_instance=beem.Hive(MASTER_NODE),
                lazy=True,
            ).get_following()
        )

    def _parse_feeds(self, urls: set[str], rewind_from: datetime) -> None:
        for podcast in Podcast.objects.filter(
            Q(parsed__isnull=True) | Q(parsed__lt=rewind_from),
            rss__in=urls,
        ):
            try:
                feed_parser.FeedParser(podcast).parse()

            except FeedParserError:
                self.stdout.write(self.style.ERROR(f"{podcast} not updated"))
            else:
                self.stdout.write(self.style.SUCCESS(f"{podcast} updated"))
