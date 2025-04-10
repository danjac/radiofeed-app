import logging

from allauth.account.models import EmailAddress
from scheduler import job

from radiofeed import tokenizer
from radiofeed.http_client import get_client
from radiofeed.podcasts import emails, itunes, recommender
from radiofeed.thread_pool import execute_thread_pool

logger = logging.getLogger(__name__)


@job
def send_recommendations(addresses: list[str] | None = None) -> None:
    """Send recommendation emails to users."""
    recipients = EmailAddress.objects.filter(
        user__is_active=True,
        user__send_email_notifications=True,
    ).select_related("user")

    if addresses:
        recipients = recipients.filter(email__in=addresses)
    else:
        recipients = recipients.filter(primary=True, verified=True)

    execute_thread_pool(emails.send_recommendations_email, recipients)


@job
def create_recommendations():
    """Generate recommendations based on podcast similarity."""
    execute_thread_pool(recommender.recommend, tokenizer.NLTK_LANGUAGES)


@job
def fetch_itunes_chart(**options):
    """Crawl iTunes Top Chart."""
    for feed in itunes.fetch_chart(get_client(), **options):
        logger.debug("Fetched itunes feed: %s", feed)
