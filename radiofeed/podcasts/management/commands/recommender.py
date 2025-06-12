import typer
from allauth.account.models import EmailAddress
from django.contrib.sites.models import Site
from django.core.mail import get_connection
from django.db import transaction
from django.db.models.functions import Lower
from django_typer.management import Typer

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool
from radiofeed.users.emails import get_recipients, send_notification_email

app = Typer(name="recommender")


@app.command("create")
def create_recommendations() -> None:
    """Create recommendations for all podcasts"""
    languages = (
        Podcast.objects.annotate(language_code=Lower("language"))
        .filter(language_code__in=tokenizer.get_language_codes())
        .values_list("language_code", flat=True)
        .order_by("language_code")
        .distinct()
    )
    execute_thread_pool(recommender.recommend, languages)
    typer.secho("Recommendations created for all podcasts", fg="green")


@app.command("send")
def send_recommendations(num_podcasts: int = 6) -> None:
    """Send podcast recommendations to users"""

    site = Site.objects.get_current()
    connection = get_connection()

    def _send_recommendations_email(recipient: EmailAddress) -> None:
        if podcasts := (
            Podcast.objects.published()
            .recommended(recipient.user)
            .order_by("-relevance", "itunes_ranking", "-pub_date")
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
                    connection=connection,
                )

                recipient.user.recommended_podcasts.add(*podcasts)

                typer.secho(
                    f"{len(podcasts)} recommendations sent to {recipient.user}",
                    fg="green",
                )

    execute_thread_pool(_send_recommendations_email, get_recipients())
