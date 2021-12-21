from __future__ import annotations

import json

from datetime import timedelta
from typing import Generator

import beem

from beem.account import Account
from beem.blockchain import Blockchain
from django.db.models import Q
from django.utils import timezone

from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast

WATCHED_OPERATION_IDS = ["podping"]


def get_stream(
    since: timedelta, acc_name: str = "podping"
) -> Generator[dict, None, None]:

    allowed_accounts = set(
        Account(
            acc_name,
            blockchain_instance=beem.Hive(node="https://api.hive.blog"),
            lazy=True,
        ).get_following()
    )

    blockchain = Blockchain(mode="head", blockchain_instance=beem.Hive())

    stream = blockchain.stream(
        opNames=["custom_json"],
        raw_ops=False,
        threading=False,
        start=blockchain.get_estimated_block_num(timezone.now() - since),
    )

    for post in stream:

        if (
            post["id"] in WATCHED_OPERATION_IDS
            and set(post["required_posting_auths"]) & allowed_accounts
        ):
            yield post


def run(since: timedelta, **scheduling_kwargs) -> Generator[str, None, None]:
    """Outputs URLs one by one as they appear on the Hive Podping stream"""

    for post in get_stream(since):

        data = json.loads(post.get("json", ""))

        if urls := [data["url"]] if "url" in data else data.get("urls", []):
            scheduler.schedule_podcast_feeds(
                Podcast.objects.filter(
                    Q(parsed__isnull=True) | Q(parsed__lt=timezone.now() - since),
                    rss__in=urls,
                ),
                **scheduling_kwargs,
            )
            yield from urls
