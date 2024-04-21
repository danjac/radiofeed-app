from datetime import timedelta

from django.db.models import OuterRef, Subquery
from django.utils import timezone

from radiofeed.emails import send_email
from radiofeed.episodes.models import Episode
from radiofeed.podcasts.models import Podcast
from radiofeed.users.models import User


def send_new_episodes_email(
    user: User,
    *,
    num_episodes: int = 6,
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

    exclude_episode_ids = (
        set(user.bookmarks.values_list("episode", flat=True))
        | set(user.audio_logs.values_list("episode", flat=True))
        | set(user.recommended_episodes.values_list("pk", flat=True))
    )

    # we want to have just one episode/podcast
    # for example, if a podcast has 3 episodes in past 24 hours, just show the latest

    if not (
        latest_episode_ids := set(
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
    ):
        return

    if episodes := (
        Episode.objects.filter(pk__in=latest_episode_ids)
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
