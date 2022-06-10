from __future__ import annotations

from django_rq import job

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Recommendation, Subscription
from radiofeed.users.emails import send_user_notification_email
from radiofeed.users.models import User


@job("emails")
def send_recommendations_email(
    user_id: int,
    min_podcasts: int = 2,
    max_podcasts: int = 3,
) -> bool:

    try:
        user = User.objects.email_notification_recipients().get(pk=user_id)
    except User.DoesNotExist:
        return False

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

    recommendations = (
        Recommendation.objects.filter(podcast__pk__in=podcast_ids)
        .exclude(
            recommended__pk__in=podcast_ids
            | set(user.recommended_podcasts.distinct().values_list("pk", flat=True))
        )
        .values_list("recommended", flat=True)
    )

    podcasts = Podcast.objects.filter(pk__in=set(recommendations)).distinct()[
        :max_podcasts
    ]

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
