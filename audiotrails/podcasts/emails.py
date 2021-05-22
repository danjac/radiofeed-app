from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template import loader

from audiotrails.podcasts.models import Podcast, Recommendation
from audiotrails.shared.types import AuthenticatedUser


def send_recommendations_email(user: AuthenticatedUser) -> None:
    """Sends email with 2 or 3 recommended podcasts, based on:
    - favorites
    - follows
    - play history
    - play queue

    Podcasts should be just recommended once to each user.
    """
    recommendations = (
        Recommendation.objects.for_user(user)
        .select_related("recommended")
        .order_by("-frequency", "-similarity")
        .values("recommended")
        .distinct()[:3]
    )

    podcasts = Podcast.objects.filter(pk__in=recommendations)

    if len(podcasts) not in (2, 3):
        return

    user.recommended_podcasts.add(*podcasts)

    site = Site.objects.get_current()

    context = {
        "recipient": user,
        "site": site,
        "protocol": "https" if settings.SECURE_SSL_REDIRECT else "http",
        "podcasts": podcasts,
    }

    message = loader.render_to_string("podcasts/emails/recommendations.txt", context)
    html_message = loader.render_to_string(
        "podcasts/emails/recommendations.html", context
    )
    send_mail(
        f"[{site.name}] Hi {user.username}, here are some new podcasts you might like!",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
    )
