from __future__ import annotations

from django.core.management.base import BaseCommand

from jcasts.episodes.models import Episode
from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def handle(self, *args, **options) -> None:

        for_update = []

        for counter, podcast in enumerate(
            Podcast.objects.active().published().iterator()
        ):

            self.stdout.write(f"{counter}: {podcast.title}")

            pub_dates = list(
                Episode.objects.filter(podcast=podcast).values_list(
                    "pub_date", flat=True
                )
            )

            podcast.frequency = scheduler.get_frequency(pub_dates)
            podcast.scheduled = scheduler.schedule(podcast.pub_date, podcast.frequency)
            podcast.queued = None

            for_update.append(podcast)

        Podcast.objects.bulk_update(
            for_update,
            fields=[
                "frequency",
                "scheduled",
                "queued",
            ],
            batch_size=1000,
        )
