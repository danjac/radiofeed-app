import logging

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.mail import get_connection
from django.db import transaction

from radiofeed import tokenizer
from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes, recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.scheduler import scheduler
from radiofeed.thread_pool import execute_thread_pool
from radiofeed.users.emails import get_recipients, send_notification_email

logger = logging.getLogger(__name__)


@scheduler.scheduled_job("cron", id="podcasts.fetch_itunes_chart", hour=9)
def fetch_itunes_chart(
    limit: int = 30,
    country: str = settings.ITUNES_CHART_COUNTRY,
):
    """Crawl iTunes Top Chart."""
    try:
        for feed in itunes.fetch_chart(get_client(), country, limit=limit):
            logger.info("Fetched itunes feed: %s", feed)
    except itunes.ItunesError as e:
        logger.exception(e)


@scheduler.scheduled_job("cron", id="podcasts.create_recommendations", hour=6)
def create_recommendations():
    """Generate recommendations based on podcast similarity."""
    for language in tokenizer.NLTK_LANGUAGES:
        logger.info("Generating recommendations for %s", language)
        recommender.recommend(language)


@scheduler.scheduled_job(
    "cron",
    id="podcasts.send_recommendations",
    hour=9,
    minute=15,
    day_of_week="fri",
)
def send_recommendations(num_podcasts: int = 6):
    """Send recommendations to users."""
    connection = get_connection()
    for future in execute_thread_pool(
        lambda recipient: _send_recommendations_email(
            recipient,
            num_podcasts,
            connection=connection,
        ),
        get_recipients(),
    ):
        try:
            future.result()
        except Exception as e:
            logger.exception(e)


def _send_recommendations_email(
    recipient: EmailAddress,
    num_podcasts: int,
    **kwargs,
) -> None:
    if podcasts := (
        Podcast.objects.published()
        .recommended(recipient.user)
        .order_by(
            "-relevance",
            "-promoted",
            "-pub_date",
        )
    )[:num_podcasts]:
        with transaction.atomic():
            logger.info(
                "Sending %d recommendations to %s", num_podcasts, recipient.email
            )
            send_notification_email(
                recipient,
                f"Hi, {recipient.user.name}, here are some podcasts you might like!",
                "podcasts/emails/recommendations.html",
                {
                    "podcasts": podcasts,
                },
                **kwargs,
            )

            recipient.user.recommended_podcasts.add(*podcasts)
