from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
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
    podcast_ids = (
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

    podcasts = (
        Podcast.objects.filter(
            Q(
                pk__in=set(
                    Recommendation.objects.filter(
                        podcast__pk__in=podcast_ids
                    ).values_list("recommended", flat=True)
                )
            )
            | Q(promoted=True),
            private=False,
        )
        .exclude(
            pk__in=set(podcast_ids)
            | set(user.recommended_podcasts.values_list("pk", flat=True))
        )
        .distinct()
        .order_by("?")
    )[:max_podcasts]

    if len(podcasts) < min_podcasts:
        return False

    user.recommended_podcasts.add(*podcasts)

    context = {
        "podcasts": podcasts,
        "recipient": user,
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
