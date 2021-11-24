from __future__ import annotations

import secrets

from datetime import timedelta

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

        time_selection = range(0, 3 * 60)

        for counter, podcast in enumerate(
            Podcast.objects.active().fresh().order_by("-pub_date").iterator()
        ):

            podcast.frequency = scheduler.get_frequency(
                list(podcast.episode_set.values_list("pub_date", flat=True))
            )

            podcast.parsed = now - timedelta(minutes=secrets.choice(time_selection))

            self.stdout.write(f"{counter}:{podcast.title}")

            for_update.append(podcast)

        Podcast.objects.bulk_update(
            for_update,
            fields=["frequency", "parsed"],
            batch_size=500,
        )
