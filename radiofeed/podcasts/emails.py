from django.db.models import Case, Value, When

from radiofeed.mail import send_templated_mail
from radiofeed.podcasts.models import Podcast, Recommendation, Subscription
from radiofeed.users.models import User


def send_recommendations_email(
    user: User, num_podcasts: int = 6, **email_settings
) -> None:
    """Sends email to user with a list of recommended podcasts.

    Recommendations based on their subscriptions or latest promoted podcasts.

    Recommended podcasts are saved to the database, so the user is not recommended the same podcasts more than once.

    If no matching podcasts are found, no email is sent.
    """

    subscribed_podcast_ids = set(
        Subscription.objects.filter(subscriber=user).values_list("podcast", flat=True)
    )

    # exclude any podcasts already recommended or subscribed

    exclude_podcast_ids = subscribed_podcast_ids | set(
        user.recommended_podcasts.values_list("pk", flat=True)
    )

    # pick highest matches

    recommended_ids = set(
        Recommendation.objects.with_relevance()
        .filter(podcast__pk__in=subscribed_podcast_ids)
        .exclude(recommended__pk__in=exclude_podcast_ids)
        .order_by("-relevance")
        .values_list("recommended", flat=True)[:num_podcasts]
    )

    # include recommended + promoted

    podcasts = (
        Podcast.objects.annotate(
            priority=Case(
                When(pk__in=recommended_ids, then=Value(2)),
                When(promoted=True, then=Value(1)),
                default=Value(0),
            )
        )
        .filter(
            priority__gt=0,
            private=False,
            pub_date__isnull=False,
        )
        .exclude(pk__in=exclude_podcast_ids)
        .order_by("-priority", "-pub_date")
    )[:num_podcasts]

    if podcasts:
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
