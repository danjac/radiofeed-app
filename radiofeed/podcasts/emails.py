from __future__ import annotations

from django.utils.translation import gettext as _
from django.utils.translation import override

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Recommendation, Subscription
from radiofeed.users.emails import send_user_notification_email
from radiofeed.users.models import User


def send_recommendations_email(
    user: User, min_podcasts: int = 2, max_podcasts: int = 3
) -> bool:
    """Sends email to user with a list of recommended podcasts.

    Recommendaitons based on their subscriptions and listening history.

    Recommended podcasts are saved to the database, so the user is not recommended the same podcasts more than once.

    Args:
        user: authenticated user
        min_podcasts: minimum number of podcasts: if less than this amount then no email is sent
        max_podcasts: maximum number of podcasts to include in email

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

    podcasts = Podcast.objects.filter(pk__in=recommended_ids).distinct()[:max_podcasts]

    if len(podcasts) < min_podcasts:
        return False

    user.recommended_podcasts.add(*podcasts)

    with override(user.language):

        send_user_notification_email(
            user,
            _("Hi {username}, here are some new podcasts you might like!").format(
                username=user.username
            ),
            "podcasts/emails/recommendations.txt",
            "podcasts/emails/recommendations.html",
            {
                "podcasts": podcasts,
            },
        )

    return True
