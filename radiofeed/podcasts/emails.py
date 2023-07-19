from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.template import loader

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Recommendation, Subscription
from radiofeed.users.models import User


def send_recommendations_email(user: User, num_podcasts: int = 6) -> None:
    """Sends email to user with a list of recommended podcasts.

    Recommendations based on their subscriptions and listening history, or latest promoted podcasts.

    Recommended podcasts are saved to the database, so the user is not recommended the same podcasts more than once.

    If no matching podcasts are found, no email is sent.
    """

    # listened, bookmark, subscribed

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

    # pick highest matches

    recommended_ids = set(
        Recommendation.objects.filter(podcast__pk__in=podcast_ids)
        .select_related("recommended")
        .order_by(
            "-similarity",
            "-frequency",
        )
        .values_list("recommended", flat=True)[:num_podcasts]
    )

    # include recommended + promoted
    # exclude any podcasts already recommended/subscribed/listened etc

    podcasts = (
        Podcast.objects.filter(
            Q(pk__in=recommended_ids) | Q(promoted=True),
            private=False,
        )
        .exclude(
            pk__in=podcast_ids
            | set(user.recommended_podcasts.values_list("pk", flat=True))
        )
        .order_by("-pub_date")
    )[:num_podcasts]

    if podcasts.exists():
        user.recommended_podcasts.add(*podcasts)

        context = {
            "podcasts": podcasts,
            "recipient": user,
        }

        send_mail(
            f"Hi {user.first_name or user.username}, here are some new podcasts you might like!",
            loader.render_to_string("podcasts/emails/recommendations.txt", context),
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=loader.render_to_string(
                "podcasts/emails/recommendations.html", context
            ),
            fail_silently=False,
        )
