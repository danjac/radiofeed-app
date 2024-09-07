import djclick as click

from radiofeed import tokenizer
from radiofeed.podcasts import emails, recommender
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor
from radiofeed.users.models import User


@click.group(invoke_without_command=True)
def cli():
    """Podcasts commands."""


@cli.command(name="create_recommendations")
def create_recommendations() -> None:
    "Create podcast recommendations."
    with DatabaseSafeThreadPoolExecutor() as executor:
        executor.db_safe_map(
            lambda language: recommender.recommend(language),
            tokenizer.NLTK_LANGUAGES,
        )


@cli.command(name="send_recommendations_emails")
def send_recommendations_emails() -> None:
    """Send recommendations emails to subscribers."""

    with DatabaseSafeThreadPoolExecutor() as executor:
        executor.db_safe_map(
            emails.send_recommendations_email,
            User.objects.filter(
                is_active=True,
                send_email_notifications=True,
            ),
        )
