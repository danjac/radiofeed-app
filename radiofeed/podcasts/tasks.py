import logging

from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models.functions import Lower
from django_q.brokers import get_broker
from django_q.tasks import async_task

from radiofeed import tokenizer
from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes, recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.users.emails import get_recipients, send_notification_email

logger = logging.getLogger(__name__)


def fetch_top_itunes(country: str, limit: int = 30) -> None:
    """Fetch the top iTunes podcasts for a given country."""

    try:
        for feed in itunes.fetch_chart(get_client(), country, limit):
            logger.info("Fetched iTunes feed: %s", feed)
    except itunes.ItunesError as exc:
        logger.error("Error fetching iTunes feed for %s: %s", country, exc)


def create_recommendations() -> None:
    """Create recommendations for all podcasts"""
    languages = (
        Podcast.objects.annotate(language_code=Lower("language"))
        .filter(language_code__in=tokenizer.get_language_codes())
        .values_list("language_code", flat=True)
        .order_by("language_code")
        .distinct()
    )

    for language in languages:
        recommender.recommend(language)
        logger.info("Recommendations created for language: %s", language)


def send_recommendations(num_podcasts: int = 6) -> None:
    """Send podcast recommendations to users"""

    broker = get_broker()

    logger.info("Sending podcast recommendations to users...")

    for recipient_id in get_recipients().values_list("id", flat=True):
        async_task(
            send_recommendations_email,
            recipient_id,
            num_podcasts=num_podcasts,
            broker=broker,
        )


def send_recommendations_email(recipient_id: int, num_podcasts: int) -> None:
    """Send podcast recommendations email to a specific recipient."""

    recipient = get_recipients().get(pk=recipient_id)

    if podcasts := (
        Podcast.objects.published()
        .recommended(recipient.user)
        .order_by("-relevance", "itunes_ranking", "-pub_date")
    )[:num_podcasts]:
        site = Site.objects.get_current()

        with transaction.atomic():
            send_notification_email(
                site,
                recipient,
                f"Hi, {recipient.user.name}, here are some podcasts you might like!",
                "podcasts/emails/recommendations.html",
                {
                    "podcasts": podcasts,
                    "site": site,
                },
            )

            recipient.user.recommended_podcasts.add(*podcasts)
            logger.info("%d podcasts sent to %s", len(podcasts), recipient.user)
