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
    execute_thread_pool(_create_recommendations, languages)


@app.command("send")
def send_recommendations(num_podcasts: int = 6) -> None:
    """Send podcast recommendations to users"""

    site = Site.objects.get_current()
    connection = get_connection()

    execute_thread_pool(
        lambda recipient: _send_recommendations_email(
            site,
            recipient,
            num_podcasts,
            connection=connection,
        ),
        get_recipients(),
    )


def _create_recommendations(language: str) -> None:
    recommender.recommend(language)
    typer.secho(f"Recommendations created for language: {language}", fg="green")


def _send_recommendations_email(
    site: Site,
    recipient: EmailAddress,
    num_podcasts: int,
    **kwargs,
) -> None:
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
                **kwargs,
            )

            recipient.user.recommended_podcasts.add(*podcasts)

            typer.secho(
                f"{len(podcasts)} recommendations sent to {recipient.user}",
                fg="green",
            )
