from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def handle(self, *args, **options) -> None:

        Podcast.objects.filter(frequency__isnull=False).update(frequency=None)

        for_update = []
        now = timezone.now()

        for podcast in Podcast.objects.active().fresh():

            podcast.frequency = scheduler.get_frequency(
                list(podcast.episode_set.values_list("pub_date", flat=True))
            )
            podcast.parsed = now

            self.stdout.write(podcast.title)

            for_update.append(podcast)

        Podcast.objects.bulk_update(
            for_update,
            fields=["frequency", "parsed"],
            batch_size=500,
        )
