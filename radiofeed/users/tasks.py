import datetime
import logging
import random
from typing import TYPE_CHECKING

from django.contrib.sites.models import Site
from django.db.models import Exists, OuterRef, QuerySet
from django.tasks import task  # type: ignore[reportMissingTypeStubs]
from django.utils import timezone

from radiofeed.episodes.models import Episode
from radiofeed.podcasts.models import Podcast
from radiofeed.users.notifications import get_recipients, send_notification_email

if TYPE_CHECKING:
    from allauth.account.models import EmailAddress

    from radiofeed.users.models import User


logger = logging.getLogger(__name__)


@task
def send_podcast_recommendations(*, recipient_id: int, limit: int = 6) -> None:
    """Send podcast recommendations to users."""

    recipient = _get_recipient(recipient_id)
    if (
        podcasts := Podcast.objects.published()
        .recommended(recipient.user)
        .order_by("-relevance", "-pub_date")[:limit]
    ):
        site = Site.objects.get_current()

        send_notification_email(
            site,
            recipient,
            f"Hi, {recipient.user.name}, here are some podcasts you might like!",
            "podcasts/emails/recommendations.html",
            {
                "podcasts": podcasts,
            },
        )
        recipient.user.recommended_podcasts.add(*podcasts)
        logger.info("Sent podcast recommendations to user %s", recipient.user)


@task
def send_episode_updates(
    *,
    recipient_id: int,
    days_since: int = 7,
    limit: int = 6,
) -> None:
    """Send podcast recommendations to users."""

    recipient = _get_recipient(recipient_id)
    since = timezone.now() - datetime.timedelta(days=days_since)

    if episodes := _get_new_episodes(recipient.user, since=since, limit=limit):
        site = Site.objects.get_current()

        send_notification_email(
            site,
            recipient,
            f"Hi, {recipient.user.name}, check out these new podcast episodes!",
            "episodes/emails/notifications.html",
            {
                "episodes": episodes,
            },
        )
        logger.info("Sent episode updates to %s", recipient.user)


def _get_recipient(recipient_id) -> EmailAddress:
    return get_recipients().select_related("user").get(pk=recipient_id)


def _get_new_episodes(
    user: User,
    *,
    since: datetime.datetime,
    limit: int,
) -> QuerySet[Episode]:
    # Fetch latest episode IDs for each podcast the user is subscribed to since given time
    # Exclude any that the user has bookmarked or listened to
    episodes = dict(
        Episode.objects.annotate(
            is_bookmarked=Exists(
                user.bookmarks.filter(
                    episode=OuterRef("pk"),
                )
            ),
            is_listened=Exists(
                user.audio_logs.filter(
                    episode=OuterRef("pk"),
                )
            ),
            is_subscribed=Exists(
                user.subscriptions.filter(
                    podcast=OuterRef("podcast"),
                )
            ),
        )
        .filter(
            is_bookmarked=False,
            is_listened=False,
            is_subscribed=True,
            pub_date__gte=since,
        )
        .order_by("pub_date", "pk")
        .values_list("podcast", "pk")
    )
    # Randomly sample up to `limit` episode IDs
    if episode_ids := list(episodes.values()):
        sample_ids = random.sample(episode_ids, min(len(episode_ids), limit))
        return (
            Episode.objects.filter(pk__in=sample_ids)
            .select_related("podcast")
            .order_by("-pub_date", "-pk")
        )
    return Episode.objects.none()
