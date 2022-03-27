from __future__ import annotations

from django_rq import job

from jcasts.podcasts.models import Podcast, Recommendation
from jcasts.users.emails import send_user_notification_email
from jcasts.users.models import User


@job("mail")
def send_recommendations_email(user: User) -> None:
    """Sends email with 2 or 3 recommended podcasts, based on:
    - favorites
    - follows
    - play history
    - play queue

    Podcasts should be just recommended once to each user.
    """
    recommendations = (
        Recommendation.objects.for_user(user)
        .order_by("-frequency", "-similarity")
        .values_list("recommended", flat=True)
    )

    podcasts = Podcast.objects.filter(pk__in=list(recommendations)).distinct()[:3]

    if len(podcasts) not in range(2, 7):
        return

    # save recommendations

    if podcasts:
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
