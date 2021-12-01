from __future__ import annotations

import json

from datetime import timedelta
from typing import Generator

import beem

from beem.account import Account
from beem.blockchain import Blockchain
from django.utils import timezone

from jcasts.podcasts import feed_parser
from jcasts.podcasts.models import Podcast

WATCHED_OPERATION_IDS = ["podping"]
HIVE_NODE = "https://api.hive.blog"
ACCOUNT_NAME = "podping"


def get_updates(
    from_minutes_ago: int = 15, batch_size=30
) -> Generator[str, None, None]:

    batch: set[str] = set()

    for url in get_stream(from_minutes_ago):
        print("from stream:", url)
        batch.add(url)

        if len(batch) > batch_size:
            print("batching", len(batch), "feeds")
            yield from batch_updates(batch, from_minutes_ago)
            batch = set()


def batch_updates(urls: set[str], from_minutes_ago: int) -> Generator[str, None, None]:
    """Processes batch of RSS feeds. Parse feeds of any URLs
    in the database that have not already been updated within the timeframe.
    """

    podcast_ids: set[int] = set()
    now = timezone.now()

    for podcast_id, rss in (
        Podcast.objects.active()
        .unqueued()
        .filter(
            rss__in=urls,
            parsed__lt=now - timedelta(minutes=from_minutes_ago),
        )
        .values_list("pk", "rss")
        .distinct()
    ):
        podcast_ids.add(podcast_id)
        yield rss

    if not podcast_ids:
        return

    Podcast.objects.filter(pk__in=podcast_ids).update(queued=now, podping=True)

    for podcast_id in podcast_ids:
        feed_parser.parse_podcast_feed.delay(podcast_id)


def get_stream(from_minutes_ago: int) -> Generator[str, None, None]:
    """Outputs URLs one by one as they appear on the Hive Podping stream"""

    allowed_accounts = set(
        Account(
            ACCOUNT_NAME,
            blockchain_instance=beem.Hive(node=HIVE_NODE),
            lazy=True,
        ).get_following()
    )

    blockchain = Blockchain(mode="head", blockchain_instance=beem.Hive())

    start_block = blockchain.get_estimated_block_num(
        timezone.now() - timedelta(minutes=from_minutes_ago)
    )

    stream = blockchain.stream(
        opNames=["custom_json"], raw_ops=False, threading=False, start=start_block
    )

    for post in stream:
        if (
            post["id"] in WATCHED_OPERATION_IDS
            and set(post["required_posting_auths"]) & allowed_accounts
        ):
            data = json.loads(post.get("json"))
            if url := data.get("url"):
                yield url
            elif urls := data.get("urls"):
                for url in urls:
                    yield url
