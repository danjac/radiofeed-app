from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Case, Value, When
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
    # exclude any podcasts already recommended/subscribed/listened etc

    exclude_podcast_ids = podcast_ids | set(
        user.recommended_podcasts.values_list("pk", flat=True)
    )

    # pick highest matches

    recommended_ids = set(
        Recommendation.objects.with_relevance()
        .filter(podcast__pk__in=podcast_ids)
        .exclude(recommended__in=exclude_podcast_ids)
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
