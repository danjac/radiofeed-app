import datetime
import logging
import random

from allauth.account.models import EmailAddress
from django.contrib.sites.models import Site
from django.db.models import Exists, OuterRef, QuerySet
from django.tasks import task  # type: ignore[reportMissingTypeStubs]
from django.utils import timezone

from listenwave.episodes.models import Episode
from listenwave.users.emails import send_notification_email
from listenwave.users.models import User

logger = logging.getLogger(__name__)


@task
def send_notifications(*, recipient_id: int, days_since: int, limit: int) -> None:
    """Sends episode notifications to a user."""
    recipient = EmailAddress.objects.select_related("user").get(pk=recipient_id)
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

        logger.debug("Sent episode notifications to %s", recipient.email)


def _get_new_episodes(
    user: User,
    *,
    since: datetime.datetime,
    limit: int,
) -> QuerySet[Episode]:
    # Fetch latest episode IDs for each podcast the user is subscribed to
    # Exclude any that the user has bookmarked or listened to
    # Include only those published within the last `days_since` days
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
    episode_ids = list(episodes.values())
    sample_ids = random.sample(
        episode_ids,
        min(len(episode_ids), limit),
    )
    return (
        Episode.objects.filter(pk__in=sample_ids)
        .select_related("podcast")
        .order_by("-pub_date", "-pk")
    )
