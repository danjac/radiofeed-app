from django_typer.management import TyperCommand, command

from radiofeed import tokenizer
from radiofeed.podcasts import emails, recommender
from radiofeed.thread_pool import execute_thread_pool
from radiofeed.users.models import User


class Command(TyperCommand):
    """Recommender management commands."""

    @command()
    def create(self):
        """Create recommendations for all supported languages."""
        execute_thread_pool(recommender.recommend, tokenizer.NLTK_LANGUAGES)

    @command()
    def send(self):
        """Send recommendation emails to users."""
        execute_thread_pool(
            emails.send_recommendations_email,
            User.objects.filter(
                is_active=True,
                send_email_notifications=True,
            ),
        )
