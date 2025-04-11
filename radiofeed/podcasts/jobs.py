import logging

from allauth.account.models import EmailAddress
from django.db.models import QuerySet
from scheduler import job

from radiofeed import tokenizer
from radiofeed.http_client import get_client
from radiofeed.podcasts import emails, itunes, recommender

logger = logging.getLogger(__name__)


@job
def send_recommendations(addresses: list[str] | None = None) -> None:
    """Send recommendation emails to users."""
    recipients = _get_recipients()

    if addresses:
        recipients = recipients.filter(email__in=addresses)
    else:
        recipients = recipients.filter(primary=True, verified=True)

    for recipient_id in recipients.values_list("pk", flat=True):
        send_recommendations_email.delay(recipient_id)  # type: ignore[union-attr]


@job
def send_recommendations_email(recipient_id: int) -> None:
    """Send a single recommendation email to a user."""
    recipient = _get_recipients().get(pk=recipient_id)
    logger.debug("Sending recommendation email to %s", recipient.email)
    emails.send_recommendations_email(recipient)


@job
def create_recommendations():
    """Generate recommendations based on podcast similarity."""
    logger.debug("Creating recommendations for all languages")
    for language in tokenizer.NLTK_LANGUAGES:
        recommend.delay(language)  # type: ignore[union-attr]


@job
def recommend(language: str):
    """Generate recommendations for a specific language."""
    logger.debug("Creating recommendations for %s", language)
    recommender.recommend(language)


@job
def fetch_itunes_chart(**options):
    """Crawl iTunes Top Chart."""
    for feed in itunes.fetch_chart(get_client(), **options):
        logger.debug("Fetched itunes feed: %s", feed)


def _get_recipients() -> QuerySet[EmailAddress]:
    return EmailAddress.objects.filter(
        user__is_active=True,
        user__send_email_notifications=True,
    )
