from __future__ import annotations

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template import loader

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Recommendation, Subscription
from radiofeed.users.models import User


def send_recommendations_email(
    user: User, min_podcasts: int = 2, max_podcasts: int = 3
) -> bool:
    """Sends email to user with a list of recommended podcasts.

    Recommendations based on their subscriptions and listening history.

    Recommended podcasts are saved to the database, so the user is not recommended the
    same podcasts more than once.

    If there are fewer than `min_podcasts` then no email will be sent.

    Returns:
        `True` user has been sent recommendations email
    """
    if not (
        podcast_ids := (
            set(
                Bookmark.objects.filter(user=user)
                .select_related("episode__podcast")
                .values_list("episode__podcast", flat=True)
            )
            | set(
                AudioLog.objects.filter(user=user)
                .select_related("episode__podcast")
                .values_list("episode__podcast", flat=True)
            )
            | set(
                Subscription.objects.filter(subscriber=user).values_list(
                    "podcast", flat=True
                )
            )
        )
        | set(user.recommended_podcasts.values_list("pk", flat=True))
    ):
        return False

    recommended_ids = (
        Recommendation.objects.filter(podcast__pk__in=podcast_ids)
        .exclude(recommended__pk__in=podcast_ids)
        .values_list("recommended", flat=True)
    )

    podcasts = (
        Podcast.objects.filter(pk__in=recommended_ids)
        .distinct()
        .order_by("?")[:max_podcasts]
    )

    if len(podcasts) < min_podcasts:
        return False

    user.recommended_podcasts.add(*podcasts)

    context = {
        "recipient": user,
        "podcasts": podcasts,
        "site": Site.objects.get_current(),
        "protocol": "https" if settings.SECURE_SSL_REDIRECT else "http",
    }

    send_mail(
        f"Hi {user.username}, here are some new podcasts you might like!",
        loader.render_to_string("podcasts/emails/recommendations.txt", context),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=loader.render_to_string(
            "podcasts/emails/recommendations.html", context
        ),
        fail_silently=False,
    )

    return True
