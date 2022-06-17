from __future__ import annotations

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Recommendation, Subscription
from radiofeed.users.emails import send_user_notification_email
from radiofeed.users.models import User


def recommendations(
    user: User,
    min_podcasts: int = 2,
    max_podcasts: int = 3,
) -> bool:

    podcast_ids: set[int] = (
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
        | set(Subscription.objects.filter(user=user).values_list("podcast", flat=True))
    )

    recommended_ids: set[int] = (
        Recommendation.objects.filter(podcast__pk__in=podcast_ids)
        .exclude(
            recommended__pk__in=podcast_ids
            | set(user.recommended_podcasts.distinct().values_list("pk", flat=True))
        )
        .values_list("recommended", flat=True)
    )

    podcasts = Podcast.objects.filter(pk__in=recommended_ids).distinct()[:max_podcasts]

    if len(podcasts) < min_podcasts:
        return False

    user.recommended_podcasts.add(*podcasts)

    send_user_notification_email(
        user,
        f"Hi {user.username}, here are some new podcasts you might like!",
        "podcasts/emails/recommendations.txt",
        "podcasts/emails/recommendations.html",
        {
            "podcasts": podcasts,
        },
    )

    return True
