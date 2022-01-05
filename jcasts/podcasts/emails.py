from __future__ import annotations

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template import loader
from django_rq import job

from jcasts.podcasts.models import Podcast, Recommendation
from jcasts.shared.typedefs import User


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

    site = Site.objects.get_current()

    context = {
        "recipient": user,
        "site": site,
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
