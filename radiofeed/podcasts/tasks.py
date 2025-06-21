from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models.functions import Lower

from radiofeed import tokenizer
from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes, recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.users.emails import get_recipients, send_notification_email

logger = get_task_logger(__name__)


@shared_task
def fetch_top_itunes(self, country: str, *, limit: int) -> None:
    """Fetch the top iTunes podcasts for a given country."""
    self.stdout.write(f"Fetching top {limit} iTunes podcasts for country: {country}")
    logger.info("Fetching top %d iTunes podcasts for country: %s", limit, country)

    try:
        for feed in itunes.fetch_chart(get_client(), country, limit):
            logger.info("Fetched iTunes feed: %s", feed)
    except itunes.ItunesError as exc:
        logger.error("Error fetching iTunes feed: %s", exc)


@shared_task
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


@shared_task
def send_recommendations(num_podcasts: int = 6) -> None:
    """Send recommendations emails to users about podcasts."""

    for recipient in get_recipients().values_list("pk", flat=True):
        send_recommendations_email.delay(recipient, num_podcasts)  # type: ignore [untyped-call]


@shared_task
def send_recommendations_email(recipient_id: int, num_podcasts: int = 6) -> None:
    """Send recommendations email to a specific user."""

    recipient = get_recipients().get(pk=recipient_id)

    site = Site.objects.get_current()

    for recipient in get_recipients():
        if podcasts := (
            Podcast.objects.published()
            .recommended(recipient.user)
            .order_by(
                "-relevance",
                "promoted",
                "-pub_date",
            )
        )[:num_podcasts]:
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

                logger.info(
                    "Sent recommendations email to user: %s", recipient.user.email
                )
