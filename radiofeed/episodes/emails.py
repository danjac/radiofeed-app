from datetime import timedelta

from django.db.models import Count, OuterRef, Subquery
from django.utils import timezone

from radiofeed.emails import send_email
from radiofeed.episodes.models import AudioLog, Episode
from radiofeed.podcasts.models import Podcast
from radiofeed.users.models import User


def send_new_episodes_email(
    user: User,
    *,
    num_episodes: int = 6,
    since: timedelta = timedelta(hours=24),
) -> None:
    """Sends notifications for podcasts you listen to the most (based on history)."""

    subscribed_podcast_ids = set(user.subscriptions.values_list("podcast", flat=True))
    if not subscribed_podcast_ids:
        return

    # exclude any I have listened to or bookmarked
    exclude_episode_ids = (
        set(user.bookmarks.values_list("episode", flat=True))
        | set(user.audio_logs.values_list("episode", flat=True))
        | set(user.recommended_episodes.values_list("pk", flat=True))
    )

    latest_episode_ids = set(
        Podcast.objects.annotate(
            num_listens=Count(
                AudioLog.objects.filter(user=user.pk, episode__podcast=OuterRef("pk"))
                .values("episode__podcast")
                .distinct(),
            ),
            latest_episode=Subquery(
                Episode.objects.filter(
                    podcast=OuterRef("pk"), pub_date__gte=timezone.now() - since
                )
                .exclude(pk__in=exclude_episode_ids)
                .order_by("-pub_date")
                .values("pk")[:1]
            ),
        )
        .filter(
            pk__in=subscribed_podcast_ids,
            num_listens__gt=0,
            latest_episode__isnull=False,
        )
        .order_by("-num_listens", "-pub_date")
        .values_list("latest_episode", flat=True)
    )
    if not latest_episode_ids:
        return

    if episodes := (
        Episode.objects.filter(pk__in=latest_episode_ids)
        .exclude(pk__in=exclude_episode_ids)
        .order_by("-pub_date")
        .select_related("podcast")
    )[:num_episodes]:
        user.recommended_episodes.add(*episodes)

        send_email(
            f"Hi {user.first_name or user.username}, here are some new episodes you might like!",
            [user.email],
            "episodes/emails/new_episodes.html",
            {
                "episodes": episodes,
                "recipient": user,
            },
        )
