from __future__ import annotations

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template import loader
from django.utils.translation import gettext as _
from django.utils.translation import override

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Recommendation, Subscription
from radiofeed.users.models import User


def send_recommendations_email(
    user: User, min_podcasts: int = 2, max_podcasts: int = 3
) -> bool:
    """Sends email to user with a list of recommended podcasts.

    Recommendaitons based on their subscriptions and listening history.

    Recommended podcasts are saved to the database, so the user is not recommended the same podcasts more than once.

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

    site = Site.objects.get_current()

    context = {"recipient": user, "site": site, "podcasts": podcasts}

    with override(user.language):

        send_mail(
            _("Hi {} here are some new podcasts you might like!".format(user.username)),
            loader.render_to_string("podcasts/emails/recommendations.txt", context),
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=loader.render_to_string(
                "podcasts/emails/recommendations.html", context
            ),
        )

    return True
