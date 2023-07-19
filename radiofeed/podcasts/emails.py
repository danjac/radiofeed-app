from django.conf import settings
from django.core.mail import send_mail
from django.template import loader

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Recommendation, Subscription
from radiofeed.users.models import User


def send_recommendations_email(user: User, max_podcasts: int = 6) -> None:
    """Sends email to user with a list of recommended podcasts.

    Recommendations based on their subscriptions and listening history, or latest promoted podcasts.

    Recommended podcasts are saved to the database, so the user is not recommended the
    same podcasts more than once.

    If there are fewer than `min_podcasts` then no email will be sent.
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

    # recommended already or already listened etc.

    exclude_podcast_ids = podcast_ids | set(
        user.recommended_podcasts.values_list("pk", flat=True)
    )

    # pick highest matches

    podcasts = {
        recommendation.recommended
        for recommendation in Recommendation.objects.filter(podcast__pk__in=podcast_ids)
        .exclude(recommended__pk__in=exclude_podcast_ids)
        .select_related("recommended")
        .order_by(
            "-similarity",
            "-frequency",
            "-recommended__pub_date",
        )[:max_podcasts]
    }

    # latest promotions

    if remainder := max_podcasts - len(podcasts):
        podcasts = podcasts | set(
            Podcast.objects.filter(promoted=True, private=False)
            .exclude(pk__in=exclude_podcast_ids)
            .order_by("-pub_date")[:remainder]
        )

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
