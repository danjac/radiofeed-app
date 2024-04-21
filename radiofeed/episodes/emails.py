from datetime import timedelta

from django.db.models import Count, OuterRef, Subquery
from django.utils import timezone

from radiofeed.emails import send_email
from radiofeed.episodes.models import Episode
from radiofeed.podcasts.models import Podcast
from radiofeed.users.models import User


def send_new_episodes_email(
    user: User,
    *,
    num_episodes: int = 12,
    since: timedelta = timedelta(hours=24),
) -> None:
    """Sends notifications for podcasts you listen to the most (based on history)."""

    if not (
        subscribed_podcast_ids := set(
            user.subscriptions.values_list("podcast", flat=True)
        )
    ):
        return

    # exclude any I have listened to or bookmarked

    exclude_episode_ids = set(user.bookmarks.values_list("episode", flat=True)) | set(
        user.audio_logs.values_list("episode", flat=True)
    )

    # we want to have just one episode/podcast
    # for example, if a podcast has 3 episodes in past 24 hours, just show the latest

    latest_episode_ids = set(
        Podcast.objects.annotate(
            latest_episode=Subquery(
                Episode.objects.filter(
                    podcast=OuterRef("pk"),
                    pub_date__gte=timezone.now() - since,
                )
                .exclude(pk__in=exclude_episode_ids)
                .order_by("-pub_date")
                .values("pk")[:1]
            ),
        )
        .filter(
            pk__in=subscribed_podcast_ids,
            latest_episode__isnull=False,
        )
        .values_list("latest_episode", flat=True)
    )

    if not latest_episode_ids:
        return

    # prioritize user's favorite podcasts based on history

    episodes = (
        Episode.objects.annotate(
            num_listens=Count(
                user.audio_logs.filter(episode__podcast=OuterRef("podcast")).values(
                    "episode__podcast"
                )
            ),
        )
        .filter(pk__in=latest_episode_ids)
        .exclude(pk__in=exclude_episode_ids)
        .order_by("-num_listens", "-pub_date")
        .select_related("podcast")
    )[:num_episodes]

    if episodes.exists():
        send_email(
            f"Hi {user.first_name or user.username}, here are some new episodes you might like!",
            [user.email],
            "episodes/emails/new_episodes.html",
            {
                "episodes": episodes,
                "recipient": user,
            },
        )
