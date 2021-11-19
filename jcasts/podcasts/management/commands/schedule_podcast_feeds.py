from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django_rq import job

from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Re-schedule podcast feeds"

    def handle(self, *args, **options) -> None:
        podcasts = get_queryset().order_by("-pub_date")

        for podcast_id in podcasts.values_list("pk", flat=True).iterator():
            schedule_podcast.delay(podcast_id)


@job("default")
def schedule_podcast(podcast_id: int) -> None:
    try:
        podcast = get_queryset().get(pk=podcast_id)
    except Podcast.DoesNotExist:
        return

    scheduled, frequency, modifier = scheduler.schedule(
        podcast.pub_date,
        list(podcast.episode_set.values_list("pub_date", flat=True)),
    )

    Podcast.objects.filter(pk=podcast_id,).update(
        scheduled=scheduled,
        frequency=frequency,
        frequency_modifier=modifier,
    )


def get_queryset() -> QuerySet:
    return Podcast.objects.active().filter(pub_date__isnull=False, queued__isnull=True)
