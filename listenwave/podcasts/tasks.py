import logging

from allauth.account.models import EmailAddress
from django.contrib.sites.models import Site
from django.tasks import task  # type: ignore[reportMissingTypeStubs]
from django.utils import timezone

from listenwave.http_client import get_client
from listenwave.podcasts import itunes
from listenwave.podcasts.models import Podcast
from listenwave.users.emails import send_notification_email

logger = logging.getLogger(__name__)


@task
def fetch_itunes_feeds(*, country: str, itunes_genre_id: int | None = None) -> None:
    """Fetch iTunes feeds."""
    with get_client() as client:
        if itunes_genre_id is None:
            logger.debug("Fetching most popular iTunes feed [%s]", country)
            feeds = itunes.fetch_chart(client, country)
            itunes.save_feeds_to_db(feeds, promoted=timezone.now().today())
        else:
            logger.debug(
                "Fetching iTunes feed for genre %s [%s]", itunes_genre_id, country
            )
            feeds = itunes.fetch_genre(client, country, itunes_genre_id)
            itunes.save_feeds_to_db(feeds)


@task
def send_recommendations(*, recipient_id: int, limit: int) -> None:
    """Sends podcast recommendations to a user."""
    recipient = EmailAddress.objects.select_related("user").get(pk=recipient_id)
    if (
        podcasts := Podcast.objects.published()
        .recommended(recipient.user)
        .order_by("-relevance", "-pub_date")[:limit]
    ):
        site = Site.objects.get_current()

        send_notification_email(
            site,
            recipient,
            f"Hi, {recipient.user.name}, here are some podcasts you might like!",
            "podcasts/emails/recommendations.html",
            {
                "podcasts": podcasts,
            },
        )

        recipient.user.recommended_podcasts.add(*podcasts)
        logger.debug("Sent podcast recommendations to %s", recipient.email)
