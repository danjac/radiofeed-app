from __future__ import annotations

from datetime import timedelta

from django.db.models import OuterRef, Subquery
from django.utils import timezone
from django_rq import job

from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.users.emails import send_user_notification_email
from radiofeed.users.models import User


@job("emails")
def send_new_episodes_email(
    user_id: int,
    interval: timedelta,
    min_episodes: int = 3,
    max_episodes: int = 6,
) -> bool:

    if (
        user := User.objects.email_notification_recipients().filter(pk=user_id).first()
    ) is None:
        return False

    if not (
        podcast_ids := set(
            Subscription.objects.filter(user=user).values_list("podcast", flat=True)
        )
    ):
        return False

    since = timezone.now() - interval

    episodes = (
        Episode.objects.filter(pub_date__gte=since)
        .exclude(episode_type__iexact="trailer")
        .order_by("-pub_date", "-id")
    )

    if excluded := (
        set(AudioLog.objects.filter(user=user).values_list("episode", flat=True))
        | set(Bookmark.objects.filter(user=user).values_list("episode", flat=True))
    ):

        episodes = episodes.exclude(pk__in=excluded)

    episode_ids = set(
        Podcast.objects.filter(pk__in=podcast_ids, pub_date__gte=since)
        .annotate(
            latest_episode=Subquery(
                episodes.filter(podcast=OuterRef("pk")).values("pk")[:1]
            )
        )
        .values_list("latest_episode", flat=True)
    )

    if not episode_ids:
        return False

    episodes = (
        Episode.objects.filter(pk__in=episode_ids, pub_date__gte=since)
        .exclude(episode_type__iexact="trailer")
        .select_related("podcast")
        .distinct()
        .order_by("?")
    )[:max_episodes]

    if len(episodes) < min_episodes:
        return False

    send_user_notification_email(
        user,
        f"Hi {user.username}, here are some new episodes from your collection.",
        "episodes/emails/new_episodes.txt",
        "episodes/emails/new_episodes.html",
        {
            "episodes": episodes,
        },
    )

    return True
