import djclick as click

from radiofeed import tokenizer
from radiofeed.podcasts import emails, recommender
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor
from radiofeed.users.models import User


@click.group(invoke_without_command=True)
def recommendations():
    """Recommendations commands."""


@recommendations.command(name="create")
def create() -> None:
    "Create podcast recommendations."
    with DatabaseSafeThreadPoolExecutor() as executor:
        executor.db_safe_map(
            lambda language: recommender.recommend(language),
            tokenizer.NLTK_LANGUAGES,
        )


@recommendations.command(name="send_emails")
def send_emails() -> None:
    """Send recommendations emails to subscribers."""

    with DatabaseSafeThreadPoolExecutor() as executor:
        executor.db_safe_map(
            emails.send_recommendations_email,
            User.objects.filter(
                is_active=True,
                send_email_notifications=True,
            ),
        )
