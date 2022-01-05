from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template import loader
from django_rq import job

from jcasts.episodes.models import Episode
from jcasts.shared.typedefs import User


@job("mail")
def send_new_episodes_email(user: User, since: timedelta) -> None:
    """Sends email with new episodes added to user's collection."""
    episodes = (
        Episode.objects.recommended(user, since)
        .select_related("podcast")
        .order_by("-pub_date", "-id")
    )
    if not episodes.exists():
        return

    site = Site.objects.get_current()

    context = {
        "recipient": user,
        "site": site,
        "episodes": episodes,
    }

    send_mail(
        f"[{site.name}] Hi {user.username}, here are some new episodes from your collection!",
        loader.render_to_string("episodes/emails/new_episodes.txt", context),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=loader.render_to_string(
            "episodes/emails/new_episodes.html", context
        ),
    )
