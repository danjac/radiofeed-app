from django.db.models import DecimalField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from loguru import logger

from radiofeed.mail import send_templated_mail
from radiofeed.podcasts.models import Podcast, Recommendation
from radiofeed.users.models import User


def send_recommendations_email(
    user: User, num_podcasts: int = 6, **email_settings
) -> None:
    """Sends email to user with a list of recommended podcasts.

    Recommendations based on their subscriptions or latest promoted podcasts.

    Recommended podcasts are saved to the database, so the user is not recommended the same podcasts more than once.

    If no matching podcasts are found, no email is sent.
    """

    subscribed_podcast_ids = set(user.subscriptions.values_list("podcast", flat=True))

    # exclude any podcasts already recommended or subscribed

    exclude_podcast_ids = subscribed_podcast_ids | set(
        user.recommended_podcasts.values_list("pk", flat=True)
    )

    # pick highest matches

    recommendations = (
        Recommendation.objects.with_relevance()
        .filter(podcast__pk__in=subscribed_podcast_ids, recommended=OuterRef("pk"))
        .exclude(recommended__pk__in=exclude_podcast_ids)
    ).order_by("-relevance")

    # include recommended + promoted

    podcasts = (
        Podcast.objects.published()
        .annotate(
            relevance=Coalesce(
                Subquery(
                    recommendations.values("relevance")[:1],
                ),
                0,
                output_field=DecimalField(),
            )
        )
        .filter(
            Q(relevance__gt=0) | Q(promoted=True),
            private=False,
        )
        .exclude(pk__in=exclude_podcast_ids)
        .order_by("-relevance", "-pub_date")
    )[:num_podcasts]

    if podcasts:
        logger.debug(
            "Sending recommendations email",
            email=user.email,
            num_podcasts=len(podcasts),
        )

        user.recommended_podcasts.add(*podcasts)

        send_templated_mail(
            f"Hi {user.first_name or user.username}, here are some new podcasts you might like!",
            [user.email],
            "podcasts/emails/recommendations.html",
            {
                "podcasts": podcasts,
                "recipient": user,
            },
            **email_settings,
        )
