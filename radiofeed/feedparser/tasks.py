from __future__ import annotations

from django_rq import job

from radiofeed.feedparser.feed_parser import FeedParser
from radiofeed.podcasts.models import Podcast


@job("feeds")
def parse_feed(podcast_id: int) -> None:
    """Handles single podcast feed update.

    Raises:
        PodcastDoesNotExist: if no podcast found
    """
    FeedParser(Podcast.objects.get(pk=podcast_id)).parse()
