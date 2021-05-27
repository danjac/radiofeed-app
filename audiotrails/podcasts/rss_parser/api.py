from __future__ import annotations

from audiotrails.episodes.models import Episode
from audiotrails.podcasts.models import Podcast


def parse_rss(podcast: Podcast, force_update: bool = False) -> list[Episode]:
    """Fetches RSS and generates Feed. Checks etag header if we need to do an update.
    If any errors occur (e.g. RSS unavailable or invalid RSS) the error is saved in database
    and RssParserError raised.
    """

    if feed := podcast.sync_rss_feed(force_update):
        return Episode.objects.sync_rss_feed(podcast, feed)

    return []
