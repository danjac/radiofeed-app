import logging

from django.tasks import task  # type: ignore[reportMissingTypeStubs]

from listenwave.http_client import get_client
from listenwave.podcasts import itunes

logger = logging.getLogger(__name__)


@task
def fetch_itunes_feeds(*, country: str, itunes_genre_id: int | None = None) -> None:
    """Fetch iTunes feeds."""
    with get_client() as client:
        if itunes_genre_id is None:
            logger.debug("Fetching most popular iTunes feed [%s]", country)
            feeds = itunes.fetch_chart(client, country)
            itunes.save_feeds_to_db(feeds, promoted=True)
        else:
            logger.debug(
                "Fetching iTunes feed for genre %s [%s]", itunes_genre_id, country
            )
            feeds = itunes.fetch_genre(client, country, itunes_genre_id)
            itunes.save_feeds_to_db(feeds)
