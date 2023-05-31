import json
import re
from argparse import ArgumentParser
from collections.abc import Iterator
from datetime import timedelta
from typing import Final

import beem
from beem.blockchain import Blockchain
from beem.nodelist import NodeList
from django.core.management.base import BaseCommand
from django.template.defaultfilters import pluralize
from django.utils import timezone

from radiofeed.podcasts.models import Podcast

_OPERATION_ID_RE: Final = re.compile(r"^pp_(.*)_(.*)|podping$")


class Command(BaseCommand):
    """Runs a Podping.cloud watcher"""

    help = """Runs Podping.cloud watcher."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--from",
            help="Start from last block (minutes)",
            type=int,
            default=15,
        )

    def handle(self, **options) -> None:
        """Main command method.

        Runs the podping watcher. Any podcasts in the database are queued for the feed parser.
        """
        nodelist = NodeList()
        nodelist.update_nodes()

        blockchain = Blockchain(
            blockchain_instance=beem.Hive(
                node=nodelist.get_hive_nodes(),
                debug=True,
            ),
        )

        self._parse_stream(
            blockchain.stream(
                opNames=["custom_json"],
                raw_ops=False,
                threading=False,
                start=blockchain.get_estimated_block_num(
                    timezone.now() - timedelta(minutes=options["from"])
                ),
            ),
        )

    def _parse_stream(self, stream: Iterator[dict]) -> None:
        for post in stream:
            if _OPERATION_ID_RE.match(post["id"]):
                data = json.loads(post["json"])

                urls: set[str] = set()

                urls = urls | set(data.get("iris", []))
                urls = urls | set(data.get("urls", []))

                if url := data.get("url"):
                    urls.add(url)

                self.stdout.write(f"podping urls: {urls}")

                if for_update := Podcast.objects.filter(
                    active=True, rss__in=urls
                ).update(
                    podping=True,
                    queued=timezone.now(),
                ):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{for_update} podcast{pluralize(for_update)} queued for update"
                        )
                    )
